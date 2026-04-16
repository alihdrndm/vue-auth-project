"""SaxonC-HE, run on one dedicated thread per process, with compiled stylesheets cached.

SaxonC runs inside a native (GraalVM) runtime that is bound to the thread which created
the processor; calling it from other threads crashed the runtime in testing. So one
thread owns the processor and does all Saxon work; callers on any thread submit a job
and wait for its result. A validation takes milliseconds, so serialising is cheap.
"""

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from importlib.metadata import version
from pathlib import Path

from saxonche import PySaxonProcessor, PyXsltExecutable

SAXONCHE_VERSION = version("saxonche")

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="saxon")


class _SaxonState(threading.local):
    """Lives only on the Saxon thread, so the processor is also released there at exit.

    Releasing it from another thread (for example the main thread during interpreter
    shutdown) crashes the native runtime.
    """

    def __init__(self) -> None:
        self.processor: PySaxonProcessor | None = None
        self.compiled: dict[Path, PyXsltExecutable] = {}


_state = _SaxonState()


def _run[T](job: Callable[[PySaxonProcessor], T]) -> T:
    def on_saxon_thread() -> T:
        if _state.processor is None:
            _state.processor = PySaxonProcessor(license=False)
        return job(_state.processor)

    return _executor.submit(on_saxon_thread).result()


def _executable(processor: PySaxonProcessor, stylesheet: Path) -> PyXsltExecutable:
    executable = _state.compiled.get(stylesheet)
    if executable is None:
        compiler = processor.new_xslt30_processor()
        executable = compiler.compile_stylesheet(stylesheet_file=str(stylesheet))
        _state.compiled[stylesheet] = executable
    return executable


def compile_all(stylesheets: list[Path]) -> None:
    """Compile stylesheets ahead of the first document (the worker calls this at start-up)."""

    def job(processor: PySaxonProcessor) -> None:
        for stylesheet in stylesheets:
            _executable(processor, stylesheet)

    _run(job)


def transform(stylesheet: Path, xml: str) -> str:
    """Run a stylesheet on a document given as text and return the result as text.

    `xml` must come from `xmlsafe.to_text`, never from the original bytes.
    """

    def job(processor: PySaxonProcessor) -> str:
        node = processor.parse_xml(xml_text=xml)
        result: str = _executable(processor, stylesheet).transform_to_string(xdm_node=node)
        return result

    return _run(job)


def first_match(xml: str, expressions: list[tuple[str, dict[str, str]]]) -> int | None:
    """Index of the first XPath 2.0 expression that is true for the document, if any."""

    def job(processor: PySaxonProcessor) -> int | None:
        node = processor.parse_xml(xml_text=xml)
        for index, (expression, namespaces) in enumerate(expressions):
            xpath = processor.new_xpath_processor()
            for prefix, uri in namespaces.items():
                xpath.declare_namespace(prefix, uri)
            xpath.set_context(xdm_item=node)
            if xpath.effective_boolean_value(expression):
                return index
        return None

    return _run(job)
