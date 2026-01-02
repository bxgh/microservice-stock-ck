from prometheus_client import Counter, Histogram, Gauge

class Metrics:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Metrics, cls).__new__(cls)
            cls._instance._init_metrics()
        return cls._instance

    def _init_metrics(self):
        # Task Duration
        self.task_duration = Histogram(
            "dag_task_duration_seconds",
            "Duration of individual DAG tasks",
            ["task_name", "status"]
        )
        
        # Workflow Duration
        self.workflow_duration = Histogram(
            "dag_workflow_duration_seconds",
            "Duration of full DAG workflows",
            ["workflow_name", "status"]
        )
        
        # Task Status Counts
        self.task_status = Counter(
            "dag_task_status_total",
            "Count of tasks by status",
            ["task_name", "status"]
        )
        
        # Workflow Status Counts
        self.workflow_status = Counter(
            "dag_workflow_status_total",
            "Count of workflows by status",
            ["workflow_name", "status"]
        )
        
        # Active Workers
        self.active_workers = Gauge(
            "active_workers_gauge",
            "Number of currently running worker containers"
        )

metrics = Metrics()
