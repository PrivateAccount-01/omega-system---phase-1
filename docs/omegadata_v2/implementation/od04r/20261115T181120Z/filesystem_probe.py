import ctypes,json
from ctypes import wintypes
for drive in ['C:\\','E:\\']:
 name=ctypes.create_unicode_buffer(261)
 function=ctypes.WinDLL('kernel32',use_last_error=True).GetVolumeInformationW
 function.argtypes=[wintypes.LPCWSTR,wintypes.LPWSTR,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),ctypes.POINTER(wintypes.DWORD),ctypes.POINTER(wintypes.DWORD),wintypes.LPWSTR,wintypes.DWORD]
 result=function(drive,None,0,None,None,None,name,261)
 print(json.dumps({'root':drive,'filesystem':name.value,'success':bool(result),'last_error':ctypes.get_last_error()}))
