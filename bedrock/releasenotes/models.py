import codecs
import os
from glob import glob

from django.conf import settings

import yaml
from django.http import Http404
from raven.contrib.django.raven_compat.models import client as sentry_client


class ReleaseNotFound(Exception):
    pass


class Note(object):
    id = None
    bug = None
    note = ''
    tag = None
    is_public = True
    fixed_in_release = None

    def __init__(self, data, release, id=None):
        if id is not None:
            self.id = id
        for key, value in data.items():
            if key == 'fixed_in_release':
                self.fixed_in_release = get_release(release.product, value)
            else:
                setattr(self, key, value)


class Release(object):
    CHANNELS = ['release', 'esr', 'beta', 'aurora', 'nightly']
    BASE_PATH = os.path.join(settings.RELEASE_NOTES_PATH, 'content')
    RELEASES_PATH = os.path.join(BASE_PATH, 'releases')
    SYS_REQ_PATH = os.path.join(BASE_PATH, 'system-requirements')
    product = None
    channel = None
    version = None
    release_date = None
    text = ''
    is_public = True
    bug_list = None
    bug_search_url = None
    _system_requirements = None
    _notes = None

    def __init__(self, data):
        for key, value in data['release'].items():
            if key == 'system_requirements':
                key = '_' + key
            setattr(self, key, value)

        if 'notes' in data:
            self._notes = data['notes']

    @property
    def system_requirements(self):
        if self._system_requirements:
            file_path = os.path.join(self.SYS_REQ_PATH,
                                     '{}.md'.format(self._system_requirements))
            with codecs.open(file_path, 'r', encoding='utf-8') as fp:
                return fp.read()

        return None

    @property
    def notes(self):
        if not self._notes:
            return []

        all_notes = [Note(data, self, i) for i, data in enumerate(self._notes)]
        if not settings.DEV:
            return [note for note in all_notes if note.is_public]

        return all_notes

    @property
    def major_version(self):
        return self.version.split('.', 1)[0]

    def get_bug_search_url(self):
        if self.bug_search_url:
            return self.bug_search_url

        if self.product == 'Thunderbird':
            return (
                'https://bugzilla.mozilla.org/buglist.cgi?'
                'classification=Client%20Software&query_format=advanced&'
                'bug_status=RESOLVED&bug_status=VERIFIED&bug_status=CLOSED&'
                'target_milestone=Thunderbird%20{version}.0&product=Thunderbird'
                '&resolution=FIXED'
            ).format(version=self.major_version)

        return (
            'https://bugzilla.mozilla.org/buglist.cgi?'
            'j_top=OR&f1=target_milestone&o3=equals&v3=Firefox%20{version}&'
            'o1=equals&resolution=FIXED&o2=anyexact&query_format=advanced&'
            'f3=target_milestone&f2=cf_status_firefox{version}&'
            'bug_status=RESOLVED&bug_status=VERIFIED&bug_status=CLOSED&'
            'v1=mozilla{version}&v2=fixed%2Cverified&limit=0'
        ).format(version=self.major_version)

    def equivalent_release_for_product(self, product):
        """
        Returns the release for a specified product with the same
        channel and major version with the highest minor version,
        or None if no such releases exist
        """
        major_version_file_id = get_file_id(product, self.channel, self.major_version)
        releases = glob(os.path.join(self.RELEASES_PATH, major_version_file_id + '.*'))
        if releases:
            releases = [get_release_from_file(fn) for fn in releases]
            if not settings.DEV:
                releases = [r for r in releases if r.is_public]
            return sorted(
                sorted(releases, reverse=True,
                       key=lambda r: len(r.version.split('.'))),
                reverse=True, key=lambda r: r.version.split('.')[1])[0]

        return None

    def equivalent_android_release(self):
        if self.product == 'Firefox':
            return self.equivalent_release_for_product('Firefox for Android')

    def equivalent_desktop_release(self):
        if self.product == 'Firefox for Android':
            return self.equivalent_release_for_product('Firefox')


def get_release(product, version, channel=None):
    channels = [channel] if channel else Release.CHANNELS
    if product.lower() == 'firefox extended support release':
        product = 'firefox'
        channels = ['esr']
    for channel in channels:
        file_name = get_release_file_name(product, channel, version)
        if not file_name:
            continue

        release = get_release_from_file(file_name)
        if release is not None:
            return release

    raise ReleaseNotFound()


def get_release_from_file(file_name):
    try:
        with codecs.open(file_name, 'r', encoding='utf-8') as rel_fh:
            return Release(yaml.safe_load(rel_fh))
    except Exception:
        sentry_client.captureException()
        return None


def get_release_file_name(product, channel, version):
    file_id = get_file_id(product, channel, version)
    file_name = os.path.join(Release.RELEASES_PATH, '{}.yml'.format(file_id))
    if os.path.exists(file_name):
        return file_name

    return None


def get_file_id(product, channel, version):
    product = product.lower().replace(' ', '-')
    channel = channel.lower()
    if product == 'firefox-extended-support-release':
        product = 'firefox'
        channel = 'esr'
    return '{}-{}-{}'.format(product, channel, version)


def get_release_or_404(version, product):
    try:
        release = get_release(product, version)
    except ReleaseNotFound:
        raise Http404

    if not release.is_public and not settings.DEV:
        raise Http404

    return release


def get_releases_or_404(product, channel):
    file_prefix = get_file_id(product, channel, '')
    releases = glob(os.path.join(Release.RELEASES_PATH, file_prefix + '*'))
    if releases:
        return [get_release_from_file(r) for r in releases]

    raise Http404
