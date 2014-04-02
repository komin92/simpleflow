# A intermediate definition of url data format
#
# Keys are represented in a path format
#   - ex. `metadata.h1`
#       This means `metadata` will be an object type and it
#       contains a field named `h1`
#
# Values contains
#   - type: data type of this field
#       - long: for large numeric values, such as hash value
#       - integer: for numeric values
#       - string: for string values
#       - struct: struct can contains some inner fields, but these fields
#           won't be visible when querying
#           ex. `something.redirects_from:
#               [{`id`: xx, `http_code`: xx}, {...}, ...]`
#               `redirects_from` is visible, but `redirects_from.id` is not
#           Struct's inner fields have their own types
#
#   - settings (optional): a set of setting flags of this field
#       - es:not_analyzed: this field should not be tokenized by ES
#       - es:no_index: this field should not be indexed
#       - es:multi_field: a multi_field type keeps multiple copies of the same
#           data in different format (analyzed, not_analyzed etc.)
#           In case of `multi_field`, `field_type` must be specified for
#           determine the field's type
#       - list: this field is actually a list of values in ES
#
#   - default_value (optional): the default value if this field does not
#       exist. If this key is not present, the field's default value will be
#       inferred based on its type
#       Set to `None` to avoid any default values, so if this field is missing
#       in ElasticSearch result, no default value will be added

_LONG_TYPE = 'long'
_INT_TYPE = 'integer'
_STRING_TYPE = 'string'
_BOOLEAN_TYPE = 'boolean'
_STRUCT_TYPE = 'struct'
_DATE_TYPE = 'date'

_NO_INDEX = 'es:no_index'
_NOT_ANALYZED = 'es:not_analyzed'
_DOC_VALUE = 'es:doc_values'
_LIST = 'list'
_MULTI_FIELD = 'es:multi_field'


URLS_DATA_FORMAT_DEFINITION = {
    # url property data
    "url": {
        "type": _STRING_TYPE,
        "settings": {_NOT_ANALYZED}
    },
    "url_hash": {"type": _LONG_TYPE},
    "byte_size": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "date_crawled": {
        "type": _DATE_TYPE,
        "settings": {_DOC_VALUE}
    },
    "delay_first_byte": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "delay_last_byte": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "depth": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "gzipped": {"type": _BOOLEAN_TYPE},
    "content_type": {
        "type": _STRING_TYPE,
        "settings": {_NOT_ANALYZED, _DOC_VALUE}
    },
    "host": {
        "type": _STRING_TYPE,
        "settings": {_NOT_ANALYZED, _DOC_VALUE}
    },
    "http_code": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "id": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "crawl_id": {"type": _INT_TYPE},
    "patterns": {
        "type": _LONG_TYPE,
        "settings": {
            _LIST
        }
    },
    "path": {
        "type": _STRING_TYPE,
        "settings": {_NOT_ANALYZED}
    },
    "protocol": {
        "type": _STRING_TYPE,
        "settings": {_NOT_ANALYZED, _DOC_VALUE}
    },
    "query_string": {
        "type": _STRING_TYPE,
        "settings": {_NOT_ANALYZED}
    },
    "query_string_keys": {
        "type": _STRING_TYPE,
        "settings": {_NOT_ANALYZED}
    },

    # meta tag related
    "metadata.robots.nofollow": {
        "type": _BOOLEAN_TYPE
    },
    "metadata.robots.noindex": {
        "type": _BOOLEAN_TYPE
    },

    # title tag
    "metadata.title.nb": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "metadata.title.contents": {
        "type": _STRING_TYPE,
        "settings": {_NOT_ANALYZED, _LIST}
    },
    "metadata.title.duplicates.nb": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "metadata.title.duplicates.is_first": {
        "type": _BOOLEAN_TYPE,
    },
    "metadata.title.duplicates.urls": {
        "type": _INT_TYPE,
        "settings": {_NO_INDEX, _LIST}
    },
    "metadata.title.duplicates.urls_exists": {
        "type": "boolean",
        "default_value": None
    },

    # h1 tag
    "metadata.h1.nb": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "metadata.h1.contents": {
        "type": _STRING_TYPE,
        "settings": {_NOT_ANALYZED, _LIST}
    },
    "metadata.h1.duplicates.nb": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "metadata.h1.duplicates.is_first": {
        "type": _BOOLEAN_TYPE,
    },
    "metadata.h1.duplicates.urls": {
        "type": _INT_TYPE,
        "settings": {_NO_INDEX, _LIST}
    },
    "metadata.h1.duplicates.urls_exists": {
        "type": "boolean",
        "default_value": None
    },

    # description tag
    "metadata.description.nb": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "metadata.description.contents": {
        "type": _STRING_TYPE,
        "settings": {_NOT_ANALYZED, _LIST}
    },
    "metadata.description.duplicates.nb": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "metadata.description.duplicates.is_first": {
        "type": _BOOLEAN_TYPE,
    },
    "metadata.description.duplicates.urls": {
        "type": _INT_TYPE,
        "settings": {_NO_INDEX, _LIST}
    },
    "metadata.description.duplicates.urls_exists": {
        "type": "boolean",
        "default_value": None
    },

    # h2 tag
    "metadata.h2.nb": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "metadata.h2.contents": {
        "type": _STRING_TYPE,
        "settings": {_NOT_ANALYZED, _LIST}
    },

    # h3 tag
    "metadata.h3.nb": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "metadata.h3.contents": {
        "type": _STRING_TYPE,
        "settings": {_NOT_ANALYZED, _LIST}
    },

    # incoming links, must be internal
    "inlinks_internal.nb.total": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "inlinks_internal.nb.unique": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "inlinks_internal.nb.follow.unique": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "inlinks_internal.nb.follow.total": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "inlinks_internal.nb.nofollow.total": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "inlinks_internal.nb.nofollow.combinations.link": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "inlinks_internal.nb.nofollow.combinations.meta": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "inlinks_internal.nb.nofollow.combinations.link_meta": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "inlinks_internal.urls": {
        "type": _INT_TYPE,
        "settings": {_NO_INDEX, _LIST}
    },
    "inlinks_internal.urls_exists": {
        "type": "boolean",
        "default_value": None
    },

    # internal outgoing links (destination is a internal url)
    "outlinks_internal.nb.total": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "outlinks_internal.nb.unique": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "outlinks_internal.nb.follow.unique": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "outlinks_internal.nb.follow.total": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "outlinks_internal.nb.nofollow.total": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "outlinks_internal.nb.nofollow.combinations.link": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "outlinks_internal.nb.nofollow.combinations.meta": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "outlinks_internal.nb.nofollow.combinations.robots": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "outlinks_internal.nb.nofollow.combinations.link_meta": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "outlinks_internal.nb.nofollow.combinations.link_robots": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "outlinks_internal.nb.nofollow.combinations.meta_robots": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "outlinks_internal.nb.nofollow.combinations.link_meta_robots": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "outlinks_internal.urls": {
        "type": _INT_TYPE,
        "settings": {_NO_INDEX, _LIST},
    },
    "outlinks_internal.urls_exists": {
        "type": _BOOLEAN_TYPE,
        "default_value": None
    },

    # external outgoing links (destination is a external url)
    "outlinks_external.nb.total": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "outlinks_external.nb.follow.total": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "outlinks_external.nb.nofollow.total": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "outlinks_external.nb.nofollow.combinations.link": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "outlinks_external.nb.nofollow.combinations.meta": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "outlinks_external.nb.nofollow.combinations.link_meta": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },

    # erroneous outgoing internal links
    "outlinks_errors.3xx.nb": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "outlinks_errors.3xx.urls": {
        "type": _INT_TYPE,
        "settings": {_NO_INDEX, _LIST}
    },
    "outlinks_errors.3xx.urls_exists": {
        "type": "boolean",
        "default_value": None
    },

    "outlinks_errors.4xx.nb": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "outlinks_errors.4xx.urls": {
        "type": _INT_TYPE,
        "settings": {_NO_INDEX, _LIST}
    },
    "outlinks_errors.4xx.urls_exists": {
        "type": "boolean",
        "default_value": None
    },

    "outlinks_errors.5xx.nb": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "outlinks_errors.5xx.urls": {
        "type": _INT_TYPE,
        "settings": {_NO_INDEX, _LIST}
    },
    "outlinks_errors.5xx.urls_exists": {
        "type": "boolean",
        "default_value": None
    },
    # total error_links number
    "outlinks_errors.total": {
        "type": "integer",
        "settings": {_DOC_VALUE}
    },

    # outgoing canonical link, one per page
    # if multiple, first one is taken into account
    "canonical.to.url": {
        "type": _STRUCT_TYPE,
        "values": {
            "url_str": {"type": "string"},
            "url_id": {"type": "integer"},
        },
        "settings": {
            _NO_INDEX
        }
    },
    "canonical.to.equal": {"type": _BOOLEAN_TYPE},
    "canonical.to.url_exists": {
        "type": "boolean",
        "default_value": None
    },

    # incoming canonical link
    "canonical.from.nb": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "canonical.from.urls": {
        "type": _INT_TYPE,
        "settings": {_NO_INDEX, _LIST}
    },
    "canonical.from.urls_exists": {
        "type": "boolean",
        "default_value": None
    },

    # outgoing redirection
    "redirect.to.url": {
        "type": _STRUCT_TYPE,
        "values": {
            "url_str": {"type": "string"},
            "url_id": {"type": "integer"},
            "http_code": {"type": "integer"}
        },
        "settings": {
            _NO_INDEX
        }
    },
    "redirect.to.url_exists": {
        "type": _BOOLEAN_TYPE,
        "default_value": None
    },

    # incoming redirection
    "redirect.from.nb": {
        "type": _INT_TYPE,
        "settings": {_DOC_VALUE}
    },
    "redirect.from.urls": {
        "type": _INT_TYPE,
        "settings": {_NO_INDEX, _LIST}
    },
    "redirect.from.urls_exists": {
        "type": "boolean",
        "default_value": None
    },
}
