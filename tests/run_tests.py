import unittest
import sys
import os
from datetime import datetime
import traceback

class DetailedTextTestResult(unittest.TextTestResult):
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.detailed_failures = []
        self.detailed_errors = []

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.detailed_failures.append((test, self._exc_info_to_string(err, test)))

    def addError(self, test, err):
        super().addError(test, err)
        self.detailed_errors.append((test, self._exc_info_to_string(err, test)))

    def getDetailedFailures(self):
        return self.detailed_failures

    def getDetailedErrors(self):
        return self.detailed_errors

class DetailedTextTestRunner(unittest.TextTestRunner):
    def _makeResult(self):
        return DetailedTextTestResult(self.stream, self.descriptions, self.verbosity)

def run_tests():
    """テストを実行する"""
    # テストディレクトリのパスを設定
    test_dir = os.path.dirname(os.path.abspath(__file__))
    
    # テストスイートの作成
    loader = unittest.TestLoader()
    suite = loader.discover(test_dir, pattern='test_*.py')
    
    # テスト結果の出力先を設定
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    result_dir = os.path.join(test_dir, 'results')
    os.makedirs(result_dir, exist_ok=True)
    
    # テスト結果のファイル名を設定
    result_file = os.path.join(result_dir, f'test_results_{timestamp}.txt')
    
    # テストの実行
    with open(result_file, 'w', encoding='utf-8') as f:
        runner = DetailedTextTestRunner(stream=f, verbosity=2)
        result = runner.run(suite)
        
        # テスト結果のサマリーを出力
        f.write('\n' + '='*50 + '\n')
        f.write('テスト結果サマリー\n')
        f.write('='*50 + '\n')
        f.write(f'実行日時: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write(f'実行したテスト数: {result.testsRun}\n')
        f.write(f'成功: {result.testsRun - len(result.failures) - len(result.errors)}\n')
        f.write(f'失敗: {len(result.failures)}\n')
        f.write(f'エラー: {len(result.errors)}\n')
        
        # 失敗したテストの詳細を出力
        if result.failures:
            f.write('\n失敗したテスト:\n')
            for failure in result.getDetailedFailures():
                f.write(f'\n{failure[0]}\n')
                f.write(f'{failure[1]}\n')
        
        # エラーが発生したテストの詳細を出力
        if result.errors:
            f.write('\nエラーが発生したテスト:\n')
            for error in result.getDetailedErrors():
                f.write(f'\n{error[0]}\n')
                f.write(f'{error[1]}\n')

        # すべてのテストケースの詳細なトレースバックを標準出力にも出す
        if result.failures or result.errors:
            print('\n--- テスト失敗・エラー詳細 ---')
            for failure in result.getDetailedFailures():
                print(f'\nFAIL: {failure[0]}')
                print(failure[1])
            for error in result.getDetailedErrors():
                print(f'\nERROR: {error[0]}')
                print(error[1])
    
    # コンソールにも結果を出力
    print(f'\nテスト結果は {result_file} に保存されました。')
    
    # テスト結果を返す
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1) 