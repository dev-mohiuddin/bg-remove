"""
onnxruntime compatibility shim for Python 3.14+.

onnxruntime's C extension DLL fails to load on Python 3.14.4 (Windows).
This module provides a minimal shim that allows rembg to import onnxruntime
without crashing, by providing the bare minimum API that rembg needs.

When onnxruntime is genuinely needed (BiRefNet inference), we attempt the
real import. If it fails, the pipeline falls back to rembg.
"""

from __future__ import annotations

import logging
import sys
import types

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Try the real onnxruntime first
# ---------------------------------------------------------------------------

_real_onnxruntime = None
_using_shim = False

try:
    import onnxruntime as _real_onnxruntime
    # Verify it actually works by calling a simple function
    _ = _real_onnxruntime.get_available_providers()
    logger.info("onnxruntime loaded successfully: %s", _real_onnxruntime.__version__)
except Exception:
    _real_onnxruntime = None
    logger.warning(
        "onnxruntime C extension failed to load (Python %s). "
        "Installing a shim for rembg compatibility. "
        "BiRefNet will be unavailable; falling back to rembg IS-Net.",
        sys.version.split()[0],
    )

    # Create a minimal shim module that rembg can import without crashing.
    _shim = types.ModuleType("onnxruntime")
    _shim.__version__ = "0.0.0-shim"
    _shim.__file__ = __file__

    def _noop(*args, **kwargs):
        pass

    _shim.set_default_logger_severity = _noop
    _shim.get_all_providers = lambda: ["CPUExecutionProvider"]
    _shim.get_available_providers = lambda: ["CPUExecutionProvider"]
    _shim.get_device = lambda: "CPU"

    # SessionOptions mock.
    class _SessionOptions:
        def __init__(self):
            self.graph_optimization_level = 99
            self.intra_op_num_threads = 1
            self.inter_op_num_threads = 1
            self.enable_cpu_mem_arena = True
            self.enable_mem_reuse = True
            self.log_severity_level = 2
            self.log_verbosity_level = 0
            self.optimized_model_filepath = ""
            self.enable_profiling = False
            self.profile_file_prefix = ""
            self.execution_mode = 0
            self.execution_order = 0
            self.logid = ""
            self.custom_ops = []
            self._extra = {}

        def add_session_config_entry(self, key, value):
            self._extra[key] = value

    _shim.SessionOptions = _SessionOptions
    _shim.GraphOptimizationLevel = type("GO", (), {"ORT_ENABLE_ALL": 99})

    # InferenceSession mock that raises a clear error if actually used for inference.
    class _ShimInferenceSession:
        """Mock session that allows construction but fails on run()."""

        def __init__(self, model_path, sess_options=None, providers=None, **kwargs):
            self._model_path = model_path
            self._providers = providers or ["CPUExecutionProvider"]
            self._inputs = [type("Inp", (), {"name": "input"})()]
            self._outputs = [type("Out", (), {"name": "output"})()]

        def get_inputs(self):
            return self._inputs

        def get_outputs(self):
            return self._outputs

        def get_providers(self):
            return self._providers

        def run(self, output_names, input_feed):
            raise RuntimeError(
                "onnxruntime is not available on Python 3.14+. "
                "Cannot run ONNX inference. The pipeline will use "
                "the rembg fallback instead."
            )

    _shim.InferenceSession = _ShimInferenceSession

    # Register the shim so rembg can import it.
    sys.modules["onnxruntime"] = _shim
    _using_shim = True


def is_available() -> bool:
    """Check if the real onnxruntime is available."""
    return _real_onnxruntime is not None


def get_session() -> object | None:
    """Return the real onnxruntime module, or None."""
    return _real_onnxruntime