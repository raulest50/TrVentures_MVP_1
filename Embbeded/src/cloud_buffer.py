"""
Buffer local de muestras cuando la subida a la nube esta deshabilitada.
Mantiene un backlog FIFO limitado y un resumen sencillo para la UI local.
"""

import ujson as json

BUFFER_FILE = "cloud_buffer.json"
MAX_PENDING_SAMPLES = 10

DEFAULT_BUFFER = {
    "pending_samples": [],
}


def _normalize_sample(sample):
    return {
        "timestamp": str(sample.get("timestamp", "")),
        "deployment_id": sample.get("deployment_id"),
        "co2": float(sample.get("co2", 0.0)),
        "temp": float(sample.get("temp", 0.0)),
        "rh": float(sample.get("rh", 0.0)),
        "errors": int(sample.get("errors", 0)),
    }


def load_buffer():
    try:
        with open(BUFFER_FILE, "r") as f:
            data = json.load(f)
    except OSError:
        data = DEFAULT_BUFFER.copy()
        save_buffer(data)
        return data
    except Exception:
        data = DEFAULT_BUFFER.copy()
        save_buffer(data)
        return data

    if not isinstance(data, dict):
        data = DEFAULT_BUFFER.copy()
    if "pending_samples" not in data or not isinstance(data["pending_samples"], list):
        data["pending_samples"] = []
    return data


def save_buffer(data):
    try:
        with open(BUFFER_FILE, "w") as f:
            json.dump(data, f)
        return True
    except Exception as e:
        print("Error guardando cloud_buffer.json: {}".format(e))
        return False


def append_sample(sample):
    data = load_buffer()
    pending_samples = data.get("pending_samples", [])
    pending_samples.append(_normalize_sample(sample))
    if len(pending_samples) > MAX_PENDING_SAMPLES:
        pending_samples = pending_samples[-MAX_PENDING_SAMPLES:]
    data["pending_samples"] = pending_samples
    save_buffer(data)
    return get_cloud_summary()


def clear_pending_samples():
    data = DEFAULT_BUFFER.copy()
    save_buffer(data)
    return get_cloud_summary()


def get_pending_samples():
    data = load_buffer()
    return data.get("pending_samples", [])


def _count_if(samples, field_name, expected_value):
    count = 0
    for sample in samples:
        if sample.get(field_name) == expected_value:
            count += 1
    return count


def get_cloud_summary(cloud_upload_enabled=None):
    samples = get_pending_samples()
    return {
        "cloud_upload_enabled": cloud_upload_enabled,
        "pending_sample_count": len(samples),
        "pending_samples": samples,
        "zero_co2_count": _count_if(samples, "co2", 0.0),
        "zero_temp_count": _count_if(samples, "temp", 0.0),
        "zero_rh_count": _count_if(samples, "rh", 0.0),
        "error_sample_count": sum(1 for sample in samples if int(sample.get("errors", 0)) > 0),
    }
