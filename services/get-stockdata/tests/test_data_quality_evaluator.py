import unittest
import sys
import os
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from core.data_quality_evaluator import DataQualityEvaluator, QualityStatus

class TestDataQualityEvaluator(unittest.TestCase):
    
    def setUp(self):
        self.evaluator = DataQualityEvaluator()
        
    def test_evaluate_pass(self):
        """Test PASS case"""
        report = {
            'columns': {
                'price': {'missing_rate': 0.0, 'count': 100},
                'volume': {'missing_rate': 0.01, 'count': 100}
            }
        }
        result = self.evaluator.evaluate(report)
        self.assertEqual(result['status'], QualityStatus.PASS.value)
        self.assertEqual(len(result['issues']), 0)
        
    def test_evaluate_fail_missing_rate(self):
        """Test failure due to high missing rate"""
        report = {
            'columns': {
                'price': {'missing_rate': 0.06, 'count': 100},  # > 5%
                'volume': {'missing_rate': 0.01, 'count': 100}
            }
        }
        result = self.evaluator.evaluate(report)
        self.assertEqual(result['status'], QualityStatus.FAIL.value)
        self.assertEqual(len(result['issues']), 1)
        self.assertEqual(result['issues'][0]['type'], 'completeness')
        self.assertIn('缺失率', result['issues'][0]['message'])

    def test_evaluate_empty_report(self):
        """Test empty report"""
        result = self.evaluator.evaluate({})
        self.assertEqual(result['status'], QualityStatus.FAIL.value)
        
    def test_custom_config(self):
        """Test custom configuration"""
        config = {'max_missing_rate': 0.10}
        evaluator = DataQualityEvaluator(config)
        
        report = {
            'columns': {
                'price': {'missing_rate': 0.08, 'count': 100}  # < 10% but > 5%
            }
        }
        result = evaluator.evaluate(report)
        self.assertEqual(result['status'], QualityStatus.PASS.value)

if __name__ == '__main__':
    unittest.main()
