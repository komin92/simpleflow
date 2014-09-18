from itertools import (
    takewhile,
    islice,
    count
)


def bulk(client, docs, chunk_size=500, bulk_type='index', **kwargs):
    bulk_actions = []
    for d in docs:
        action = {bulk_type: {}}
        for key in ('_id', '_index', '_parent', '_percolate', '_routing',
                    '_timestamp', '_ttl', '_type', '_version',):
            if key in d:
                action[bulk_type][key] = d.pop(key)

        bulk_actions.append(action)
        bulk_actions.append(d.get('_source', d))

    if not bulk_actions:
        return {}

    return client.bulk(bulk_actions, **kwargs)


def _chunk(stream, size):
    """Chunk the stream
    """
    _stream = iter(stream)
    return takewhile(bool, (list(islice(_stream, size)) for _ in count()))


def multi_get(client, index, doc_type, ids, fields, routing, chunk_size=500):
    """Issue a multi get to ElasticSearch, retrieve some fields

    ElasticSearch's `multi-get` end point returns documents like:
        {
            u'_type': doc_type,
            u'found': True,
            u'_index': index_name,
            u'_source': {...},
            u'_version': 1,
            u'_id': _id
        }

    This helper returns a list of parsed multi-get results:
        (id, doc, found)
    id and doc default to `None`, found defaults to False

    Warning: fields will not be validated by our data model, use with care
        and prepare for exceptions

    :param client: ElasticSearch client
    :type client: Elasticsearch
    :param index: index name
    :type index: str
    :param doc_type: document type in the index
    :type doc_type: str
    :param ids: iterable of document id
    :type ids: iterable
    :param fields: fields to retrieve, will not be validated
    :type fields: list
    :param chunk_size: size of each request to ElasticSearch
    :type chunk_size: int
    :param routing: routing for ElasticSearch request
    :type routing: str | int
    :return: list of retrieved sub documents (dict)
    :rtype: list
    """
    results = []
    for trunk in _chunk(ids, chunk_size):
        resolved = client.mget(
            body={"ids": trunk},
            index=index,
            doc_type=doc_type,
            routing=routing,
            preference=routing,
            _source=fields
        )
        results.extend(
            [(d.get('_id'), d.get('_source'), d.get('found', False))
             for d in resolved['docs']]
        )
    return results