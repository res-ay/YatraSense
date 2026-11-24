from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ml_service import workflows as w
if __name__=='__main__':
    print(w.ingest());print(w.preprocess_crowd())
    for task in ['crowd','recommendation']:
        if task=='recommendation':print(w.preprocess_recommendation())
        print(w.train(task));print(w.evaluate_validation(task));print(w.select(task));print(w.final_test(task)['test'])
