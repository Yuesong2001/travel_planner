"""
LangSmith Monitoring and Performance Analysis Module
Used for tracking, analyzing, and optimizing application performance.
"""

from typing import Dict, Any, List, Optional
import time
import json
from datetime import datetime
from collections import defaultdict


class PerformanceMonitor:
    """Performance Monitor
    
    Tracks key metrics:
    - Response time
    - Token usage
    - Error rate
    - Execution time for each node
    """
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = defaultdict(list)
        self.error_log: List[Dict[str, Any]] = []
        self.session_data: List[Dict[str, Any]] = []
    
    def log_response_time(self, node_name: str, elapsed_time: float):
        """Logs the response time of a node."""
        self.metrics[f"{node_name}_response_time"].append(elapsed_time)
    
    def log_token_usage(self, node_name: str, token_count: int):
        """Logs token usage."""
        self.metrics[f"{node_name}_tokens"].append(token_count)
    
    def log_error(self, node_name: str, error: str, context: Dict[str, Any]):
        """Logs an error."""
        self.error_log.append({
            "timestamp": datetime.now().isoformat(),
            "node": node_name,
            "error": error,
            "context": context
        })
    
    def log_session(self, session_data: Dict[str, Any]):
        """Logs complete session data."""
        session_data["timestamp"] = datetime.now().isoformat()
        self.session_data.append(session_data)
    
    def get_average_response_time(self, node_name: str) -> float:
        """Gets the average response time."""
        key = f"{node_name}_response_time"
        if key in self.metrics and self.metrics[key]:
            return sum(self.metrics[key]) / len(self.metrics[key])
        return 0.0
    
    def get_error_rate(self, node_name: Optional[str] = None) -> float:
        """Gets the error rate."""
        if node_name:
            errors = [e for e in self.error_log if e["node"] == node_name]
            total = len([s for s in self.session_data if node_name in str(s)])
        else:
            errors = self.error_log
            total = len(self.session_data)
        
        return len(errors) / total if total > 0 else 0.0
    
    def generate_report(self) -> str:
        """Generates a performance report."""
        report = ["# Performance Monitoring Report\n"]
        report.append(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report.append(f"Total Sessions: {len(self.session_data)}\n")
        report.append(f"Total Errors: {len(self.error_log)}\n\n")
        
        # Response time statistics
        report.append("## Response Time Statistics\n")
        for key, values in self.metrics.items():
            if "response_time" in key:
                node = key.replace("_response_time", "")
                avg = sum(values) / len(values) if values else 0
                report.append(f"- {node}: {avg:.3f}s (avg), {min(values):.3f}s (min), {max(values):.3f}s (max)\n")
        
        # Token usage statistics
        report.append("\n## Token Usage Statistics\n")
        for key, values in self.metrics.items():
            if "tokens" in key:
                node = key.replace("_tokens", "")
                total = sum(values)
                avg = total / len(values) if values else 0
                report.append(f"- {node}: {total} tokens (total), {avg:.1f} tokens (avg)\n")
        
        # Error statistics
        report.append("\n## Error Statistics\n")
        if self.error_log:
            error_by_node = defaultdict(int)
            for error in self.error_log:
                error_by_node[error["node"]] += 1
            
            for node, count in error_by_node.items():
                report.append(f"- {node}: {count} errors\n")
        else:
            report.append("No errors recorded\n")
        
        return "".join(report)
    
    def export_to_json(self, filepath: str):
        """Exports data to a JSON file."""
        data = {
            "metrics": dict(self.metrics),
            "errors": self.error_log,
            "sessions": self.session_data,
            "generated_at": datetime.now().isoformat()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def identify_bottlenecks(self) -> List[Dict[str, Any]]:
        """Identifies performance bottlenecks."""
        bottlenecks = []
        
        # Find nodes with response times over 2 seconds
        for key, values in self.metrics.items():
            if "response_time" in key:
                node = key.replace("_response_time", "")
                avg_time = sum(values) / len(values) if values else 0
                
                if avg_time > 2.0:
                    bottlenecks.append({
                        "node": node,
                        "issue": "slow_response",
                        "avg_time": avg_time,
                        "severity": "high" if avg_time > 5.0 else "medium",
                        "recommendation": "Consider optimizing prompt length or using a faster model."
                    })
        
        # Find nodes with error rates over 5%
        for node in set(e["node"] for e in self.error_log):
            error_rate = self.get_error_rate(node)
            if error_rate > 0.05:
                bottlenecks.append({
                    "node": node,
                    "issue": "high_error_rate",
                    "error_rate": error_rate,
                    "severity": "high" if error_rate > 0.1 else "medium",
                    "recommendation": "Check input validation and exception handling logic."
                })
        
        return bottlenecks
    
    def get_optimization_suggestions(self) -> List[str]:
        """Gets optimization suggestions."""
        suggestions = []
        bottlenecks = self.identify_bottlenecks()
        
        if not bottlenecks:
            suggestions.append("✓ System is running well, no significant bottlenecks found.")
        else:
            for bottleneck in bottlenecks:
                suggestions.append(
                    f"⚠ [{bottleneck['severity'].upper()}] {bottleneck['node']}: "
                    f"{bottleneck['recommendation']}"
                )
        
        # General suggestions
        total_sessions = len(self.session_data)
        if total_sessions > 10:
            avg_chat_time = self.get_average_response_time("chat")
            avg_planner_time = self.get_average_response_time("planner")
            
            if avg_chat_time > 0 and avg_planner_time > avg_chat_time * 3:
                suggestions.append(
                    "💡 The Planner node is significantly slower than the Chat node. "
                    "Suggestions:\n"
                    "  1. Simplify the prompt template.\n"
                    "  2. Reduce the number of tool calls.\n"
                    "  3. Enable response caching."
                )
        
        return suggestions


class LangSmithAnalyzer:
    """LangSmith Data Analyzer
    
    Analyzes run data fetched from LangSmith.
    """
    
    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor
    
    def analyze_prompt_performance(
        self,
        prompt_versions: Dict[str, List[float]]
    ) -> Dict[str, Any]:
        """Analyzes the performance of different prompt versions.
        
        Args:
            prompt_versions: {version_name: [list_of_response_times]}
        
        Returns:
            Analysis results.
        """
        results = {}
        
        for version, times in prompt_versions.items():
            results[version] = {
                "avg_time": sum(times) / len(times) if times else 0,
                "min_time": min(times) if times else 0,
                "max_time": max(times) if times else 0,
                "count": len(times)
            }
        
        # Find the fastest version
        if results:
            best_version = min(results.items(), key=lambda x: x[1]["avg_time"])
            results["recommendation"] = {
                "best_version": best_version[0],
                "improvement": (
                    max(r["avg_time"] for r in results.values()) -
                    best_version[1]["avg_time"]
                ) / max(r["avg_time"] for r in results.values()) * 100
            }
        
        return results
    
    def compare_with_baseline(
        self,
        current_metrics: Dict[str, float],
        baseline_metrics: Dict[str, float]
    ) -> Dict[str, Any]:
        """Compares with baseline metrics.
        
        Args:
            current_metrics: The current metrics.
            baseline_metrics: The baseline metrics.
        
        Returns:
            Comparison results.
        """
        comparison = {}
        
        for metric, current_value in current_metrics.items():
            if metric in baseline_metrics:
                baseline_value = baseline_metrics[metric]
                change = ((current_value - baseline_value) / baseline_value * 100)
                
                comparison[metric] = {
                    "current": current_value,
                    "baseline": baseline_value,
                    "change_percent": change,
                    "improved": change < 0  # For time-based metrics, a decrease is an improvement
                }
        
        return comparison
    
    def generate_insights(self) -> str:
        """Generates data insights."""
        insights = ["# Data Insights\n\n"]
        
        bottlenecks = self.monitor.identify_bottlenecks()
        
        if bottlenecks:
            insights.append("## Issues Found\n")
            for i, bottleneck in enumerate(bottlenecks, 1):
                insights.append(f"{i}. {bottleneck['node']} - {bottleneck['issue']}\n")
                insights.append(f"   Recommendation: {bottleneck['recommendation']}\n\n")
        
        suggestions = self.monitor.get_optimization_suggestions()
        if suggestions:
            insights.append("## Optimization Suggestions\n")
            for suggestion in suggestions:
                insights.append(f"- {suggestion}\n")
        
        return "".join(insights)


# Singleton instance
_monitor_instance = None


def get_monitor() -> PerformanceMonitor:
    """Gets the global monitor instance."""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = PerformanceMonitor()
    return _monitor_instance


# Example usage
if __name__ == "__main__":
    monitor = get_monitor()
    
    # Simulate some data
    monitor.log_response_time("chat", 1.2)
    monitor.log_response_time("chat", 1.5)
    monitor.log_response_time("planner", 3.2)
    monitor.log_response_time("planner", 2.8)
    
    monitor.log_token_usage("chat", 150)
    monitor.log_token_usage("planner", 500)
    
    # Generate report
    print(monitor.generate_report())
    
    # Analyze bottlenecks
    print("\n" + "="*50)
    print("Performance Bottleneck Analysis:")
    print("="*50)
    bottlenecks = monitor.identify_bottlenecks()
    for b in bottlenecks:
        print(f"- {b}")
    
    # Optimization suggestions
    print("\n" + "="*50)
    print("Optimization Suggestions:")
    print("="*50)
    for suggestion in monitor.get_optimization_suggestions():
        print(suggestion)
