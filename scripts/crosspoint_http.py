"""Drive the guest CrossPoint server through isolated loopback forwarding."""
import hashlib
import json
import time
import urllib.request


def exercise(directory,payload,seconds):
    deadline=time.monotonic()+seconds
    result=dict(completed=False,payload_sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload))
    def request(path,body=None,headers=None):
        req=urllib.request.Request('http://127.0.0.1:18080'+path,data=body,headers=headers or {})
        with urllib.request.urlopen(req,timeout=30) as response:return response.read()
    try:
        while time.monotonic()<deadline:
            try:
                status=json.loads(request('/api/status'));break
            except (OSError,ValueError):time.sleep(0.1)
        else:raise TimeoutError('CrossPoint server did not become reachable')
        body=b'--lab\r\nContent-Disposition: form-data; name="file"; filename="LABUPLOAD.epub"\r\nContent-Type: application/epub+zip\r\n\r\n'+payload+b'\r\n--lab--\r\n'
        upload=request('/upload?path=/',body,{'Content-Type':'multipart/form-data; boundary=lab'})
        returned=request('/download?path=/LABUPLOAD.epub')
        result.update(status=status,upload_response=upload.decode(errors='replace'),
            downloaded_bytes=len(returned),downloaded_sha256=hashlib.sha256(returned).hexdigest(),completed=returned==payload)
    except (OSError,ValueError,TimeoutError) as error:result['error']=str(error)
    (directory/'http-result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
