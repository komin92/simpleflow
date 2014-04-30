from cdf.metadata.url.url_metadata import (
    INT_TYPE, ES_DOC_VALUE, AGG_NUMERICAL
)
from cdf.core.features import StreamDefBase
from .settings import ORGANIC_SOURCES, SOCIAL_SOURCES


class RawVisitsStreamDef(StreamDefBase):
    FILE = 'analytics_raw_data'
    HEADERS = (
        ('url', str),
        ('medium', str),
        ('source', str),
        ('social_network', lambda i: i.lower() if i != '(not set)' else None),
        ('nb_visits', int),
    )


class VisitsStreamDef(StreamDefBase):
    FILE = 'analytics_data'
    HEADERS = (
        ('id', int),
        ('medium', str),
        ('source', str),
        ('social_network', str),
        ('nb_visits', int),
    )
    URL_DOCUMENT_MAPPING = {
        "visits.organic.google.nb": {
            "type": INT_TYPE,
            "settings": {
                ES_DOC_VALUE,
                AGG_NUMERICAL
            }
        },
        "visits.organic.bing.nb": {
            "type": INT_TYPE,
            "settings": {
                ES_DOC_VALUE,
                AGG_NUMERICAL
            }
        },
        "visits.organic.yahoo.nb": {
            "type": INT_TYPE,
            "settings": {
                ES_DOC_VALUE,
                AGG_NUMERICAL
            }
        },
        "visits.social.facebook.nb": {
            "type": INT_TYPE,
            "settings": {
                ES_DOC_VALUE,
                AGG_NUMERICAL
            }
        },
        "visits.social.twitter.nb": {
            "type": INT_TYPE,
            "settings": {
                ES_DOC_VALUE,
                AGG_NUMERICAL
            }
        },
        "visits.social.pinterest.nb": {
            "type": INT_TYPE,
            "settings": {
                ES_DOC_VALUE,
                AGG_NUMERICAL
            }
        }
    }

    def pre_process_document(self, document):
        document["visits"] = {
            "organic": {
                "google": {
                    "nb": 0
                },
                "bing": {
                    "nb": 0
                },
                "yahoo": {
                    "nb": 0
                }
            },
            "social": {
                "facebook": {
                    "nb": 0
                },
                "twitter": {
                    "nb": 0
                },
                "pinterest": {
                    "nb": 0
                }
            }
        }

    def process_document(self, document, stream):
        _, medium, source, social_network, nb_visits = stream
        if social_network and social_network in SOCIAL_SOURCES:
            document['visits']['social'][social_network]['nb'] += nb_visits
        elif medium == 'organic' and source in ORGANIC_SOURCES:
            document['visits'][medium][source]['nb'] = nb_visits
        return
