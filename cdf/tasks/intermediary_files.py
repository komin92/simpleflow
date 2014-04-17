import os
import gzip
import itertools

from boto.exception import S3ResponseError

from cdf.log import logger
from cdf.utils.path import write_by_part
from cdf.utils.s3 import push_file
from cdf.analysis.urls.transducers.metadata_duplicate import get_duplicate_metadata
from cdf.analysis.urls.transducers.links import OutlinksTransducer, InlinksTransducer
from cdf.utils.remote_files import nb_parts_from_crawl_location
from cdf.analysis.urls.generators.bad_links import get_bad_links, get_bad_link_counters
from cdf.features.main.streams import InfosStreamDef
from cdf.features.links.streams import (
    OutlinksRawStreamDef, OutlinksStreamDef,
    InlinksRawStreamDef, BadLinksStreamDef, BadLinksCountersStreamDef
)
from cdf.features.semantic_metadata.streams import ContentsStreamDef
from .decorators import TemporaryDirTask as with_temporary_dir
from .constants import DEFAULT_FORCE_FETCH


@with_temporary_dir
def make_links_counter_file(crawl_id, s3_uri,
                            part_id, link_direction,
                            tmp_dir=None, force_fetch=DEFAULT_FORCE_FETCH):
    if link_direction == "out":
        transducer = OutlinksTransducer
        stream_name = OutlinksRawStreamDef
    else:
        transducer = InlinksTransducer
        stream_name = InlinksRawStreamDef

    stream_links = stream_name().get_stream_from_storage(s3_uri, tmp_dir, part_id, force_fetch)
    generator = transducer(stream_links).get()

    filenames = {
        'links': 'url_{}_links_counters.txt.{}.gz'.format(link_direction, part_id),
        'canonical': 'url_{}_canonical_counters.txt.{}.gz'.format(link_direction, part_id),
        'redirect': 'url_{}_redirect_counters.txt.{}.gz'.format(link_direction, part_id),
    }

    # lazily open files
    file_created = {}
    for i, entry in enumerate(generator):
        # TODO remove hard coded index
        link_type = entry[1]
        if link_type not in file_created:
            file_created[link_type] = gzip.open(os.path.join(tmp_dir, filenames[link_type]), 'w')
        file_created[link_type].write(str(entry[0]) + '\t' + '\t'.join(str(k) for k in entry[2:]) + '\n')

    for _f in file_created.itervalues():
        _f.close()

    # push all created files to s3
    logger.info('Pushing links counter files to S3')
    for counter_file in file_created.values():
        counter_filename = os.path.basename(counter_file.name)
        logger.info('Pushing {}'.format(counter_filename))
        push_file(
            os.path.join(s3_uri, counter_filename),
            os.path.join(tmp_dir, counter_filename),
        )


@with_temporary_dir
def make_metadata_duplicates_file(crawl_id, s3_uri,
                                  first_part_id_size, part_id_size,
                                  tmp_dir=None, force_fetch=DEFAULT_FORCE_FETCH):
    def to_string(row):
        url_id, metadata_type, filled_nb, duplicates_nb, is_first, target_urls_ids = row
        return '\t'.join((
            str(url_id),
            str(metadata_type),
            str(filled_nb),
            str(duplicates_nb),
            '1' if is_first else '0',
            ';'.join(str(u) for u in target_urls_ids)
        )) + '\n'

    nb_parts = nb_parts_from_crawl_location(s3_uri)

    logger.info('Fetching all partitions from S3')
    streams = []
    for part_id in xrange(0, nb_parts):
        streams.append(
            ContentsStreamDef.get_stream_from_storage(
                s3_uri,
                tmp_dir=tmp_dir,
                part_id=part_id,
                force_fetch=force_fetch
            )
        )

    generator = get_duplicate_metadata(itertools.chain(*streams))

    file_pattern = 'urlcontentsduplicate.txt.{}.gz'
    write_by_part(generator, first_part_id_size, part_id_size,
                  tmp_dir, file_pattern, to_string)

    # push all created files to s3
    logger.info('Pushing metadata duplicate file to s3')
    for i in xrange(0, nb_parts + 1):
        file_to_push = file_pattern.format(i)
        if os.path.exists(os.path.join(tmp_dir, file_to_push)):
            logger.info('Pushing {}'.format(file_to_push))
            push_file(
                os.path.join(s3_uri, file_to_push),
                os.path.join(tmp_dir, file_to_push),
            )


@with_temporary_dir
def make_bad_link_file(crawl_id, s3_uri,
                       first_part_id_size=500000,
                       part_id_size=500000,
                       tmp_dir=None, force_fetch=DEFAULT_FORCE_FETCH):
    """
    Generate a tsv file that list all urls outlink to an error url:
      url_src_id  url_dest_id error_http_code

    Ordered on url_src_id
    """
    def to_string(row):
        return '\t'.join(str(field) for field in row) + '\n'

    streams_types = {'infos': [],
                     'outlinks': []}
    nb_parts = nb_parts_from_crawl_location(s3_uri)

    logger.info('Fetching all partition info and links files from s3')
    for part_id in xrange(0, nb_parts):
        storage_kwargs = {
            'storage_uri': s3_uri,
            'tmp_dir': tmp_dir,
            'force_fetch': force_fetch,
            'part_id': part_id
        }
        streams_types['infos'].append(InfosStreamDef.get_stream_from_storage(**storage_kwargs))
        streams_types['outlinks'].append(OutlinksStreamDef.get_stream_from_storage(**storage_kwargs))

    generator = get_bad_links(itertools.chain(*streams_types['infos']),
                              itertools.chain(*streams_types['outlinks']))

    file_pattern = 'urlbadlinks.txt.{}.gz'
    write_by_part(generator, first_part_id_size, part_id_size,
                  tmp_dir, file_pattern, to_string)

    # push all created files to s3
    logger.info('Pushing badlink files to s3')
    for i in xrange(0, nb_parts + 1):
        file_to_push = file_pattern.format(i)
        if os.path.exists(os.path.join(tmp_dir, file_to_push)):
            logger.info('Pushing {}'.format(file_to_push))
            push_file(
                os.path.join(s3_uri, file_to_push),
                os.path.join(tmp_dir, file_to_push),
            )


@with_temporary_dir
def make_bad_link_counter_file(crawl_id, s3_uri,
                               part_id,
                               tmp_dir=None,
                               force_fetch=DEFAULT_FORCE_FETCH):
    """
    Generate a counter file that list bad link counts by source url and http code
      url_src_id  http_code  count

    This method depend on the file generated by `make_bad_link_file`
    Ordered on url_src_id and http_code
    """
    stream = BadLinksStreamDef.get_stream_from_storage(s3_uri, tmp_dir=tmp_dir, force_fetch=force_fetch, part_id=part_id)
    generator = get_bad_link_counters(stream)

    file_name = 'urlbadlinks_counters.txt.%d.gz' % part_id
    f = gzip.open(os.path.join(tmp_dir, file_name), 'w')
    for src, bad_code, count in generator:
        f.write('\t'.join((
            str(src),
            str(bad_code),
            str(count)
        )) + '\n')
    f.close()

    logger.info('Pushing {}'.format(file_name))
    push_file(
        os.path.join(s3_uri, file_name),
        os.path.join(tmp_dir, file_name),
    )
