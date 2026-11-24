from pathlib import Path
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
ROOT=Path(__file__).resolve().parents[1]
def run(in_process=False):
    paths=[]
    for folder in ['crowd','recommendation','shared']:paths.extend(sorted((ROOT/'notebooks'/folder).glob('*.ipynb')))
    for path in paths:
        print('Executing',path.relative_to(ROOT),flush=True)
        nb=nbformat.read(path,as_version=4)
        if in_process:
            # Execute actual notebook code through IPython without kernel sockets.
            # This is used only for restricted build environments.
            from IPython.core.interactiveshell import InteractiveShell
            from IPython.utils.capture import capture_output
            import os
            shell=InteractiveShell.instance();shell.reset(new_session=False)
            previous=os.getcwd();os.chdir(ROOT)
            try:
                count=0
                for cell in nb.cells:
                    if cell.cell_type!='code':continue
                    count+=1;cell.execution_count=count;cell.outputs=[]
                    with capture_output(stdout=True,stderr=True,display=True) as output:
                        result=shell.run_cell(cell.source,store_history=False)
                    if result.error_before_exec or result.error_in_exec:raise result.error_before_exec or result.error_in_exec
                    if output.stdout:cell.outputs.append(nbformat.v4.new_output('stream',name='stdout',text=output.stdout))
                    if output.stderr:cell.outputs.append(nbformat.v4.new_output('stream',name='stderr',text=output.stderr))
                    for item in output.outputs:cell.outputs.append(nbformat.v4.new_output('display_data',data=item.data,metadata=item.metadata))
                nb.metadata['execution_backend']='Actual code executed through in-process IPython (build environment disallows kernel sockets)'
            finally:os.chdir(previous)
        else:
            NotebookClient(nb,timeout=900,kernel_name='python3',resources={'metadata':{'path':str(ROOT)}}).execute()
        nbformat.write(nb,path)
    print('All notebooks executed successfully.',flush=True)
if __name__=='__main__':
    import sys
    run(in_process='--in-process' in sys.argv)
