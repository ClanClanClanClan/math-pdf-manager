 ---------------------------------------------------------------------------
PermissionError                           Traceback (most recent call last)
/tmp/ipykernel_1103/1731851061.py in <cell line: 0>()
      7 if os.path.isfile(LLAMA_QUANTIZE) and os.path.isfile(LLAMA_CONVERT):
      8     # Verify cached binary still works on this VM
----> 9     result = subprocess.run([LLAMA_QUANTIZE, '--help'], capture_output=True)
     10     if result.returncode == 0:
     11         print('llama.cpp build found on Drive and verified. Skipping.')

2 frames/usr/lib/python3.12/subprocess.py in run(input, capture_output, timeout, check, *popenargs, **kwargs)
    546         kwargs['stderr'] = PIPE
    547 
--> 548     with Popen(*popenargs, **kwargs) as process:
    549         try:
    550             stdout, stderr = process.communicate(input, timeout=timeout)

/usr/lib/python3.12/subprocess.py in __init__(self, args, bufsize, executable, stdin, stdout, stderr, preexec_fn, close_fds, shell, cwd, env, universal_newlines, startupinfo, creationflags, restore_signals, start_new_session, pass_fds, user, group, extra_groups, encoding, errors, text, umask, pipesize, process_group)
   1024                             encoding=encoding, errors=errors)
   1025 
-> 1026             self._execute_child(args, executable, preexec_fn, close_fds,
   1027                                 pass_fds, cwd, env,
   1028                                 startupinfo, creationflags, shell,

/usr/lib/python3.12/subprocess.py in _execute_child(self, args, executable, preexec_fn, close_fds, pass_fds, cwd, env, startupinfo, creationflags, shell, p2cread, p2cwrite, c2pread, c2pwrite, errread, errwrite, restore_signals, gid, gids, uid, umask, start_new_session, process_group)
   1953                         err_msg = os.strerror(errno_num)
   1954                     if err_filename is not None:
-> 1955                         raise child_exception_type(errno_num, err_msg, err_filename)
   1956                     else:
   1957                         raise child_exception_type(errno_num, err_msg)

PermissionError: [Errno 13] Permission denied: '/content/drive/MyDrive/pdf-meta-llm/llama_cpp_build/build/bin/llama-quantize'