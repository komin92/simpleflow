# -*- coding: utf-8 -*-
import os
import re
import json
import copy
import operator
from pandas import HDFStore
import numpy
import itertools

from cdf.collections.suggestions.constants import CROSS_PROPERTIES_COLUMNS, COUNTERS_FIELDS

from cdf.utils.s3 import fetch_files, fetch_file
from cdf.utils.dict import deep_dict, deep_update
from cdf.streams.utils import split_file
from .utils import field_has_children, children_from_field


def is_dict_filter(filter_dict):
    """
    Check if the incoming dict is a filter (means "field" et "value" keys are set
    """
    return 'field' in filter_dict and 'value' in filter_dict


def is_boolean_operation_filter(filter_dict):
    return len(filter_dict) == 1 and filter_dict.keys()[0].lower() in ('and', 'or')


def std_type(value):
    if type(value) == numpy.bool_:
        return bool(value)
    elif type(value) == numpy.int64:
        return int(value)
    elif type(value) == numpy.float:
        if numpy.isnan(value):
            return 0
        else:
            return int(value)

    return value


class BadRequestException(Exception):
    pass


def transform_std_type(field, df_values):
    return std_type(df_values[field] if field in df_values else 0)


class BaseMetricsQuery(object):

    BadRequestException = BadRequestException

    DISTRIBUTION_COLUMNS = CROSS_PROPERTIES_COLUMNS
    FIELDS = CROSS_PROPERTIES_COLUMNS + COUNTERS_FIELDS

    def __init__(self, hdfstore, options=None):
        self.hdfstore = hdfstore

        self.df = self.hdfstore[self.DF_KEY]
        self.options = options

    @classmethod
    def from_s3_uri(cls, crawl_id, s3_uri, options=None, tmp_dir_prefix='/tmp', force_fetch=False):
        # Fetch locally the files from S3
        tmp_dir = os.path.join(tmp_dir_prefix, 'crawl_%d' % crawl_id)
        files_fetched = fetch_files(s3_uri, tmp_dir, regexp='suggest.h5', force_fetch=force_fetch)
        store = HDFStore(files_fetched[0][0])
        return cls(store, options)

    def get_func_from_filter_dict(self, df, _filter):
        # Not operator
        if _filter.get('not', False):
            _op = lambda i: operator.__not__(i)
        else:
            _op = lambda i: i

        predicate = _filter.get('predicate', None)
        if not predicate:
            if isinstance(_filter['value'], list):
                predicate = "in"
            else:
                predicate = "eq"

        if predicate == "eq":
            _predicate_func = lambda value, i: value == i
        elif predicate == "re":
            _predicate_func = lambda value, i: bool(re.search(value, i))
        elif predicate == "starts":
            _predicate_func = lambda value, i: i.startswith(value)
        elif predicate == "ends":
            _predicate_func = lambda value, i: i.endswith(value)
        elif predicate == "gte":
            _predicate_func = lambda value, i: i >= value
        elif predicate == "lte":
            _predicate_func = lambda value, i: i <= value
        elif predicate == "gt":
            _predicate_func = lambda value, i: i > value
        elif predicate == "lt":
            _predicate_func = lambda value, i: i < value
        elif predicate == "contains":
            _predicate_func = lambda value, i: value in i
        elif predicate == "in":
            _predicate_func = lambda value, i: any(i == v for v in value)

        return df[_filter['field']].map(lambda i: _op(_predicate_func(_filter['value'], i)))

    def _apply_filters_list(self, df, lst, _operator='or'):
        filters_func = None
        for _filter in lst:
            if filters_func is None:
                filters_func = self.get_func_from_filter_dict(df, _filter)
            else:
                getattr(operator, '__i%s__' % _operator)(filters_func, self.get_func_from_filter_dict(df, _filter))
        return filters_func

    def _apply_filters(self, df, filters, parent_operator="or"):
        filters_func = None
        if isinstance(filters, list):
            if filters[0].keys()[0].lower() in ('and', 'or'):
                _sub_operator_key = filters[0].keys()[0]
                filters_func = self._apply_filters_list(df, filters[0][_sub_operator_key], _operator=_sub_operator_key.lower())
            else:
                filters_func = self._apply_filters_list(df, filters, _operator=parent_operator)
        elif is_dict_filter(filters):
            return self.get_func_from_filter_dict(df, filters)
        elif is_boolean_operation_filter(filters):
            key = filters.keys()[0]
            _operator = key.lower()

            for _filter in filters[key]:
                if filters_func is None:
                    filters_func = self._apply_filters(df, _filter, parent_operator=_operator)
                else:
                    getattr(operator, "__i%s__" % _operator)(filters_func, self._apply_filters(df, _filter, parent_operator=_operator))
        else:
            raise Exception('Filter not well formated : %s' % filters)
        return filters_func

    def get_fields_from_settings(self, settings):
        if 'fields' in settings:
            fields = settings['fields']
        else:
            fields = filter(lambda i: i not in self.DISTRIBUTION_COLUMNS, self.df.columns.tolist())

        final_fields = []
        for f in fields:
            #if f not in self.FIELDS:
            #    raise self.BadRequestException('Field {} not allowed in query'.format(f))
            if field_has_children(f):
                final_fields += children_from_field(f)
            else:
                final_fields.append(f)
        return final_fields

    def query(self, settings):
        """
        Return the total sum from a list of `fields` aggregated by cross-property

        :param settings

        Return a list of dictionaries with two keys "properties" and "counters".

        Ex :

        [
            {
                "properties": {
                    "depth": 1,
                    "http_code": 200
                },
                "counters": {
                    "pages_nb": 10,
                }
            },
            {
                "properties": {
                    "depth": 1,
                    "http_code": 301
                },
                "counters": {
                    "pages_nb": 20
                }
            }
        ]
        """
        final_fields = self.get_fields_from_settings(settings)

        results = {}
        df = self.df.copy()

        if 'filters' in settings:
            df = df[self._apply_filters(df, settings['filters'])]

        if 'group_by' in settings:
            df = df.groupby(settings['group_by']).agg('sum').reset_index()
            df = self.df_filter_after_agg(df)
            if 'sort' in settings:
                df.sort(columns=[k[0] for k in settings['sort']], ascending=[k[1] == "ASC" for k in settings['sort']], inplace=True)

        else:
            """
            No group_by, we return a dictionnary with all counters
            """
            df = df.sum().reset_index()
            df = self.df_filter_after_agg(df)
            if 'sort' in settings:
                df.sort(columns=[k[0] for k in settings['sort']], ascending=[k[1] == "ASC" for k in settings['sort']], inplace=True)
            results = {}
            values = dict(df.values)
            for field in final_fields:
                deep_update(results, deep_dict({field: transform_std_type(field, values)}))
            return {"counters": results}

        results = []
        for i, n in enumerate(df.values):
            values = dict(zip(df.columns, n))
            counters = {}
            for field in final_fields:
                deep_update(counters, deep_dict({field: transform_std_type(field, values)}))
            result = {
                'properties': {field_: self._display_field(field_, values[field_]) for field_ in settings['group_by']},
                'counters': counters
            }
            results.append(result)
        return results

    def df_filter_after_agg(self, df):
        """
        Filter the dataframe after aggregation if necessary
        """
        return df

    def _display_field(self, field, value):
        return std_type(value)


class MetricsQuery(BaseMetricsQuery):
    DF_KEY = "full_crawl"


class SuggestQuery(BaseMetricsQuery):
    DF_KEY = "suggest"

    def query_hash_to_string(self, value):
        return unicode(self.hdfstore['requests'].ix[value, 'string'], "utf8")

    """
    def _display_field(self, field, value):
        if field == "query":
            return self.query_hash_to_string(value)
        return super(SuggestQuery, self)._display_field(field, value)
    """

    def query(self, settings, sort_results=True):
        final_fields = self.get_fields_from_settings(settings)
        df = self.df.copy()

        target_field = settings.get('target_field', 'pages_nb')

        if 'filters' in settings:
            df = df[self._apply_filters(df, settings['filters'])]

        df = df.groupby(['query']).agg('sum').reset_index()
        df.sort(columns=[target_field], ascending=[0], inplace=True)

        results = []
        for i, n in enumerate(df.values):
            values = dict(zip(df.columns, n))
            #counters = {}
            #for field in final_fields:
            #    deep_update(counters, deep_dict({field: transform_std_type(field, values)}))
            result = {
                'query': values['query'],
                'counters': {field: transform_std_type(field, values) for field in final_fields}
            }
            results.append(result)

        if sort_results:
            results = self.sort_results_by_target_field_count(settings, results)
            results = self.remove_equivalent_parents(settings, results)
            results = self.hide_less_relevant_children(settings, results)



        # Resolve query
        for i, r in enumerate(results):
            results[i]["query_hash_id"] = [int(v) for v in results[i]["query"].split(';')]
            results[i]["query"] = self.query_hash_to_string(results[i]["query"])
            results[i]["counters"] = deep_dict(results[i]["counters"])
            if "children" in results[i]:
                if not settings.get('display_children', True):
                    del results[i]["children"]
                    continue
                results[i]["children"] = results[i]["children"][0:10]
                for k, c in enumerate(results[i]["children"]):
                    results[i]["children"][k]["query"] = self.query_hash_to_string(results[i]["children"][k]["query"])
                    results[i]["children"][k]["counters"] = deep_dict(results[i]["children"][k]["counters"])
        return results[0:30]

    def sort_results_by_target_field_count(self, settings, results):
        """Sort the query results by target field count.
        For instance if we look for elements with title not set:
        - pattern A has size 200 and contains 10 elements with h1 not set
        - pattern B has size 110 and contains 100 elements with h1 not set

        this method will place pattern B first.
        """
        target_field = settings.get('target_field', 'pages_nb')
        results = sorted(results, reverse = True, key = lambda x: x["counters"][target_field])
        return results

    def remove_equivalent_parents(self, settings, results):
        """This method removes parent results if they have a child which
        contains the same number of relevant elements.

        For instance if we look for elements with title not set:
        - pattern A has size 200 and contains 100 elements with h1 not set
        - pattern B has size 110 and contains 100 elements with h1 not set

        pattern A is a parent of pattern B.

        Displaying pattern A to the user would not help him.
        pattern B is more relevant as it is more specific.

        The present method would remove pattern A from results
        """

        target_field = settings.get('target_field', 'pages_nb')
        if not 'children' in self.hdfstore.keys():
            return results

        child_frame = self.hdfstore['children']

        hashes_to_remove = []
        for potential_parent, potential_child in itertools.combinations(results, 2):
            potential_parent_hash = potential_parent["query"]
            potential_child_hash = potential_child["query"]

            parent_selection = (child_frame.parent == potential_parent_hash)
            child_selection = (child_frame.child == potential_child_hash)

            if child_frame[parent_selection & child_selection].shape[0] != 0:
                parent_target_field_count = potential_parent["counters"][target_field]
                child_target_field_count = potential_child["counters"][target_field]
                if parent_target_field_count == child_target_field_count:
                    hashes_to_remove.append(potential_parent_hash)

        results = [result for result in results if not result["query"] in hashes_to_remove]
        return results


    def hide_less_relevant_children(self, settings, results):
        """Once we have displayed a node,
        displaying its children would confuse the user.
        The present method :
        - detects such children
        - remove them from the result
        - add them as children of their parent

        The method requires the input results to be sorted.
        The sort criterion does not matter.
        """
        if not 'children' in self.hdfstore.keys():
            return results

        child_frame = self.hdfstore['children']

        hashes_to_remove = []
        for potential_parent, potential_child  in itertools.combinations(results, 2):
            potential_parent_hash = potential_parent["query"]
            potential_child_hash = potential_child["query"]

            parent_selection = (child_frame.parent == potential_parent_hash)
            child_selection = (child_frame.child == potential_child_hash)

            if child_frame[parent_selection & child_selection].shape[0] != 0:
                hashes_to_remove.append(potential_child_hash)
                if not "children" in potential_parent:
                    potential_parent["children"] = []
                potential_parent["children"].append(copy.copy(potential_child))

        results = [result for result in results if not result["query"] in hashes_to_remove]
        return results

    def df_filter_after_agg(self, df):
        """
        if self.options['stats_urls_done']:
            # Take only urls > 3%
            threshold = int(float(self.options['stats_urls_done']) * 0.03)
            return df[df['pages_nb'] > threshold]
        """
        return df


class SuggestSummaryQuery(object):

    def __init__(self, content):
        self.content = content

    @classmethod
    def from_s3_uri(cls, crawl_id, s3_uri, options=None, tmp_dir_prefix='/tmp', force_fetch=False):
        # Fetch locally the files from S3
        tmp_dir = os.path.join(tmp_dir_prefix, 'crawl_%d' % crawl_id)
        files_fetched = fetch_files(s3_uri, tmp_dir, regexp='suggested_patterns_summary.json', force_fetch=force_fetch)
        content = json.loads(open(files_fetched[0][0]).read())
        return cls(content)

    def get(self):
        return self.content


class SuggestedPatternsQuery(object):

    def __init__(self, stream):
        self.stream = stream

    @classmethod
    def from_s3_uri(cls, crawl_id, s3_uri, tmp_dir_prefix='/tmp', force_fetch=False):
        # Fetch locally the files from S3
        tmp_dir = os.path.join(tmp_dir_prefix, 'crawl_%d' % crawl_id, 'clusters_mixed.tsv')
        fetch_file(os.path.join(s3_uri, 'clusters_mixed.tsv'), tmp_dir, force_fetch=force_fetch)
        return cls(split_file(open(tmp_dir)))

    def get(self):
        for query, query_verbose, hash_id, nb_urls in self.stream:
            yield {
                "query": query,
                "query_verbose": query_verbose,
                "query_hash_id": hash_id,
                "nb_urls": nb_urls
            }
