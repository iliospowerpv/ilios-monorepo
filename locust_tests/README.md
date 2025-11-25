1. Each new module should be described as SequentialTaskSet.
2. If user should be logged in - inherit `LoginTasks` class and add `on_start` method to be logged in before all tasks
```
    def on_start(self):
        self.login()
```
3. Each task set should be completed with stop task which interrupts current task set execution to go to the next task set
```
    @task
    def stop(self):
        self.interrupt()
```

Example of task set:
```
class ModuleTaskSet(SequentialTaskSet, LoginTasks):


    def on_start(self):
        self.login()

    @task
    def your_task(self):
        pass


    @task
    def stop(self):
        self.interrupt()
```
