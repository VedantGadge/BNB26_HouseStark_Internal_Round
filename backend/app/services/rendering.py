"""Compatibility imports; footage inspection belongs to app.features.footage_analysis."""

from app.features.footage_analysis.probe import MediaProbe, MediaProbeError, probe_media

__all__ = ["MediaProbe", "MediaProbeError", "probe_media"]
