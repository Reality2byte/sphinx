"""Manual pages builder."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sphinx import addnodes
from sphinx._cli.util.colour import darkgreen
from sphinx.builders import Builder
from sphinx.locale import __
from sphinx.util import logging
from sphinx.util.display import progress_message
from sphinx.util.docutils import _get_settings
from sphinx.util.nodes import inline_all_toctrees
from sphinx.util.osutil import ensuredir, make_filename_from_project
from sphinx.writers.manpage import (
    ManualPageTranslator,
    ManualPageWriter,
    NestedInlineTransform,
)

if TYPE_CHECKING:
    from collections.abc import Set

    from sphinx.application import Sphinx
    from sphinx.config import Config
    from sphinx.util.typing import ExtensionMetadata

logger = logging.getLogger(__name__)


class ManualPageBuilder(Builder):
    """Builds groff output in manual page format."""

    name = 'man'
    format = 'man'
    epilog = __('The manual pages are in %(outdir)s.')

    default_translator_class = ManualPageTranslator
    supported_image_types = []

    def init(self) -> None:
        if not self.config.man_pages:
            logger.warning(
                __('no "man_pages" config value found; no manual pages will be written')
            )

    def get_outdated_docs(self) -> str | list[str]:
        return 'all manpages'  # for now

    def get_target_uri(self, docname: str, typ: str | None = None) -> str:
        return ''

    @progress_message(__('writing'))
    def write_documents(self, _docnames: Set[str]) -> None:
        docsettings = _get_settings(
            ManualPageWriter, defaults=self.env.settings, read_config_files=True
        )

        for info in self.config.man_pages:
            docname, name, description, authors, section = info
            if docname not in self.env.all_docs:
                logger.warning(
                    __('"man_pages" config value references unknown document %s'),
                    docname,
                )
                continue
            if isinstance(authors, str):
                if authors:
                    authors = [authors]
                else:
                    authors = []

            docsettings.title = name
            docsettings.subtitle = description
            docsettings.authors = authors
            docsettings.section = section

            if self.config.man_make_section_directory:
                dirname = 'man%s' % section
                ensuredir(self.outdir / dirname)
                targetname = f'{dirname}/{name}.{section}'
            else:
                targetname = f'{name}.{section}'

            logger.info('%s { ', darkgreen(targetname))

            tree = self.env.get_doctree(docname)
            docnames: set[str] = set()
            largetree = inline_all_toctrees(
                self, docnames, docname, tree, darkgreen, [docname]
            )
            largetree.settings = docsettings
            logger.info('} ', nonl=True)
            self.env.resolve_references(largetree, docname, self)
            # remove pending_xref nodes
            for pendingnode in largetree.findall(addnodes.pending_xref):
                pendingnode.replace_self(pendingnode.children)

            transform = NestedInlineTransform(largetree)
            transform.apply()
            visitor: ManualPageTranslator = self.create_translator(largetree, self)  # type: ignore[assignment]
            largetree.walkabout(visitor)
            (self.outdir / targetname).write_text(visitor.astext(), encoding='utf-8')

    def finish(self) -> None:
        pass


def default_man_pages(config: Config) -> list[tuple[str, str, str, list[str], int]]:
    """Better default man_pages settings."""
    filename = make_filename_from_project(config.project)
    return [
        (
            config.root_doc,
            filename,
            f'{config.project} {config.release}',
            [config.author],
            1,
        )
    ]


def setup(app: Sphinx) -> ExtensionMetadata:
    app.add_builder(ManualPageBuilder)

    app.add_config_value(
        'man_pages', default_man_pages, '', types=frozenset({list, tuple})
    )
    app.add_config_value('man_show_urls', False, '', types=frozenset({bool}))
    app.add_config_value(
        'man_make_section_directory', False, '', types=frozenset({bool})
    )

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
