# File: d (Python 2.4)

__all__ = [
    'Task',
    'TaskManager',
    'cont',
    'done',
    'again',
    'pickup',
    'exit',
    'sequence',
    'loop',
    'pause']
from direct.directnotify.DirectNotifyGlobal import *
from direct.showbase import ExceptionVarDump
from direct.showbase.PythonUtil import *
from direct.showbase.MessengerGlobal import messenger
import signal
import types
import time
import random
import string
from pandac.PandaModules import *

def print_exc_plus():
    pass

done = AsyncTask.DSDone
cont = AsyncTask.DSCont
again = AsyncTask.DSAgain
pickup = AsyncTask.DSPickup
exit = AsyncTask.DSExit
Task = PythonTask
Task.DtoolClassDict['done'] = done
Task.DtoolClassDict['cont'] = cont
Task.DtoolClassDict['again'] = again
Task.DtoolClassDict['pickup'] = pickup
Task.DtoolClassDict['exit'] = exit
pause = AsyncTaskPause
Task.DtoolClassDict['pause'] = staticmethod(pause)

def sequence(*taskList):
    seq = AsyncTaskSequence('sequence')
    for task in taskList:
        seq.addTask(task)
    
    return seq

Task.DtoolClassDict['sequence'] = staticmethod(sequence)

def loop(*taskList):
    seq = AsyncTaskSequence('loop')
    for task in taskList:
        seq.addTask(task)
    
    seq.setRepeatCount(-1)
    return seq

Task.DtoolClassDict['loop'] = staticmethod(loop)

class TaskManager:
    notify = directNotify.newCategory('TaskManager')
    extendedExceptions = False
    MaxEpochSpeed = 1.0 / 30.0
    
    def __init__(self):
        self.mgr = AsyncTaskManager.getGlobalPtr()
        self.resumeFunc = None
        self.globalClock = self.mgr.getClock()
        self.stepping = False
        self.running = False
        self.destroyed = False
        self.fKeyboardInterrupt = False
        self.interruptCount = 0
        self._frameProfileQueue = Queue()
        self._profileFrames = None
        self._frameProfiler = None
        self._profileTasks = None
        self._taskProfiler = None
        self._taskProfileInfo = ScratchPad(taskId = None, profiled = False, session = None)

    
    def finalInit(self):
        StateVar = StateVar
        import direct.fsm.StatePush
        self._profileTasks = StateVar(False)
        self.setProfileTasks(ConfigVariableBool('profile-task-spikes', 0).getValue())
        self._profileFrames = StateVar(False)
        self.setProfileFrames(ConfigVariableBool('profile-frames', 0).getValue())

    
    def destroy(self):
        self.notify.info('TaskManager.destroy()')
        self.destroyed = True
        self._frameProfileQueue.clear()
        self.mgr.cleanup()

    
    def setClock(self, clockObject):
        self.mgr.setClock(clockObject)
        self.globalClock = clockObject

    
    def invokeDefaultHandler(self, signalNumber, stackFrame):
        print '*** allowing mid-frame keyboard interrupt.'
        signal.signal(signal.SIGINT, signal.default_int_handler)
        raise KeyboardInterrupt

    
    def keyboardInterruptHandler(self, signalNumber, stackFrame):
        self.fKeyboardInterrupt = 1
        self.interruptCount += 1
        if self.interruptCount == 1:
            print '* interrupt by keyboard'
        elif self.interruptCount == 2:
            print '** waiting for end of frame before interrupting...'
            signal.signal(signal.SIGINT, self.invokeDefaultHandler)
        

    
    def getCurrentTask(self):
        return Thread.getCurrentThread().getCurrentTask()

    
    def hasTaskChain(self, chainName):
        return self.mgr.findTaskChain(chainName) != None

    
    def setupTaskChain(self, chainName, numThreads = None, tickClock = None, threadPriority = None, frameBudget = None, frameSync = None, timeslicePriority = None):
        chain = self.mgr.makeTaskChain(chainName)
        if numThreads is not None:
            chain.setNumThreads(numThreads)
        
        if tickClock is not None:
            chain.setTickClock(tickClock)
        
        if threadPriority is not None:
            chain.setThreadPriority(threadPriority)
        
        if frameBudget is not None:
            chain.setFrameBudget(frameBudget)
        
        if frameSync is not None:
            chain.setFrameSync(frameSync)
        
        if timeslicePriority is not None:
            chain.setTimeslicePriority(timeslicePriority)
        

    
    def hasTaskNamed(self, taskName):
        return bool(self.mgr.findTask(taskName))

    
    def getTasksNamed(self, taskName):
        return self._TaskManager__makeTaskList(self.mgr.findTasks(taskName))

    
    def getTasksMatching(self, taskPattern):
        return self._TaskManager__makeTaskList(self.mgr.findTasksMatching(GlobPattern(taskPattern)))

    
    def getAllTasks(self):
        return self._TaskManager__makeTaskList(self.mgr.getTasks())

    
    def getTasks(self):
        return self._TaskManager__makeTaskList(self.mgr.getActiveTasks())

    
    def getDoLaters(self):
        return self._TaskManager__makeTaskList(self.mgr.getSleepingTasks())

    
    def _TaskManager__makeTaskList(self, taskCollection):
        l = []
        for i in range(taskCollection.getNumTasks()):
            l.append(taskCollection.getTask(i))
        
        return l

    
    def doMethodLater(self, delayTime, funcOrTask, name, extraArgs = None, sort = None, priority = None, taskChain = None, uponDeath = None, appendTask = False, owner = None):
        if delayTime < 0:
            pass
        1
        task = self._TaskManager__setupTask(funcOrTask, name, priority, sort, extraArgs, taskChain, appendTask, owner, uponDeath)
        task.setDelay(delayTime)
        self.mgr.add(task)
        return task

    
    def add(self, funcOrTask, name = None, sort = None, extraArgs = None, priority = None, uponDeath = None, appendTask = False, taskChain = None, owner = None):
        task = self._TaskManager__setupTask(funcOrTask, name, priority, sort, extraArgs, taskChain, appendTask, owner, uponDeath)
        self.mgr.add(task)
        return task

    
    def _TaskManager__setupTask(self, funcOrTask, name, priority, sort, extraArgs, taskChain, appendTask, owner, uponDeath):
        if isinstance(funcOrTask, AsyncTask):
            task = funcOrTask
        elif hasattr(funcOrTask, '__call__'):
            task = PythonTask(funcOrTask)
        else:
            self.notify.error('add: Tried to add a task that was not a Task or a func')
        if hasattr(task, 'setArgs'):
            if extraArgs is None:
                extraArgs = []
                appendTask = True
            
            task.setArgs(extraArgs, appendTask)
        elif extraArgs is not None:
            self.notify.error('Task %s does not accept arguments.' % repr(task))
        
        if name is not None:
            task.setName(name)
        
        if priority is not None and sort is None:
            task.setSort(priority)
        elif priority is not None:
            task.setPriority(priority)
        
        if sort is not None:
            task.setSort(sort)
        
        if taskChain is not None:
            task.setTaskChain(taskChain)
        
        if owner is not None:
            task.setOwner(owner)
        
        if uponDeath is not None:
            task.setUponDeath(uponDeath)
        
        return task

    
    def remove(self, taskOrName):
        if isinstance(taskOrName, types.StringTypes):
            tasks = self.mgr.findTasks(taskOrName)
            return self.mgr.remove(tasks)
        elif isinstance(taskOrName, AsyncTask):
            return self.mgr.remove(taskOrName)
        elif isinstance(taskOrName, types.ListType):
            for task in taskOrName:
                self.remove(task)
            
        else:
            self.notify.error('remove takes a string or a Task')

    
    def removeTasksMatching(self, taskPattern):
        tasks = self.mgr.findTasksMatching(GlobPattern(taskPattern))
        return self.mgr.remove(tasks)

    
    def step(self):
        self.fKeyboardInterrupt = 0
        self.interruptCount = 0
        signal.signal(signal.SIGINT, self.keyboardInterruptHandler)
        startFrameTime = self.globalClock.getRealTime()
        self.mgr.poll()
        nextTaskTime = self.mgr.getNextWakeTime()
        self.doYield(startFrameTime, nextTaskTime)
        signal.signal(signal.SIGINT, signal.default_int_handler)
        if self.fKeyboardInterrupt:
            raise KeyboardInterrupt
        

    
    def run(self):
        self.stop()
        continue
        except IOError:
            ioError = None
            (code, message) = self._unpackIOError(ioError)
            if code == 4:
                self.stop()
            else:
                raise 
            code == 4
            except Exception:
                e = None
                if self.extendedExceptions:
                    self.stop()
                    print_exc_plus()
                elif ExceptionVarDump.wantStackDumpLog and ExceptionVarDump.dumpOnExceptionInit:
                    ExceptionVarDump._varDump__print(e)
                
                raise 
                continue
                if self.extendedExceptions:
                    self.stop()
                    print_exc_plus()
                else:
                    raise 
            
        self.mgr.stopThreads()

    
    def _unpackIOError(self, ioError):
        
        try:
            (code, message) = ioError
        except:
            code = 0
            message = ioError

        return (code, message)

    
    def stop(self):
        self.running = False

    
    def _TaskManager__tryReplaceTaskMethod(self, task, oldMethod, newFunction):
        if not isinstance(task, PythonTask):
            return 0
        
        method = task.getFunction()
        if type(method) == types.MethodType:
            function = method.im_func
        else:
            function = method
        if function == oldMethod:
            import new as new
            newMethod = new.instancemethod(newFunction, method.im_self, method.im_class)
            task.setFunction(newMethod)
            return 1
        
        return 0

    
    def replaceMethod(self, oldMethod, newFunction):
        numFound = 0
        for task in self.getAllTasks():
            numFound += self._TaskManager__tryReplaceTaskMethod(task, oldMethod, newFunction)
        
        return numFound

    
    def popupControls(self):
        TaskManagerPanel = TaskManagerPanel
        import direct.tkpanels
        return TaskManagerPanel.TaskManagerPanel(self)

    
    def getProfileSession(self, name = None):
        if name is None:
            name = 'taskMgrFrameProfile'
        
        ProfileSession = ProfileSession
        import direct.showbase.ProfileSession
        return ProfileSession(name)

    
    def profileFrames(self, num = None, session = None, callback = None):
        if num is None:
            num = 1
        
        if session is None:
            session = self.getProfileSession()
        
        session.acquire()
        self._frameProfileQueue.push((num, session, callback))

    
    def _doProfiledFrames(self, numFrames):
        for i in xrange(numFrames):
            result = self.step()
        
        return result

    
    def getProfileFrames(self):
        return self._profileFrames.get()

    
    def getProfileFramesSV(self):
        return self._profileFrames

    
    def setProfileFrames(self, profileFrames):
        self._profileFrames.set(profileFrames)
        if not (self._frameProfiler) and profileFrames:
            FrameProfiler = FrameProfiler
            import direct.task.FrameProfiler
            self._frameProfiler = FrameProfiler()
        

    
    def getProfileTasks(self):
        return self._profileTasks.get()

    
    def getProfileTasksSV(self):
        return self._profileTasks

    
    def setProfileTasks(self, profileTasks):
        self._profileTasks.set(profileTasks)
        if not (self._taskProfiler) and profileTasks:
            TaskProfiler = TaskProfiler
            import direct.task.TaskProfiler
            self._taskProfiler = TaskProfiler()
        

    
    def logTaskProfiles(self, name = None):
        if self._taskProfiler:
            self._taskProfiler.logProfiles(name)
        

    
    def flushTaskProfiles(self, name = None):
        if self._taskProfiler:
            self._taskProfiler.flush(name)
        

    
    def _setProfileTask(self, task):
        if self._taskProfileInfo.session:
            self._taskProfileInfo.session.release()
            self._taskProfileInfo.session = None
        
        self._taskProfileInfo = ScratchPad(taskFunc = task.getFunction(), taskArgs = task.getArgs(), task = task, profiled = False, session = None)
        task.setFunction(self._profileTask)
        task.setArgs([
            self._taskProfileInfo], True)

    
    def _profileTask(self, profileInfo, task):
        appendTask = False
        taskArgs = profileInfo.taskArgs
        if taskArgs and taskArgs[-1] == task:
            appendTask = True
            taskArgs = taskArgs[:-1]
        
        task.setArgs(taskArgs, appendTask)
        task.setFunction(profileInfo.taskFunc)
        ProfileSession = ProfileSession
        import direct.showbase.ProfileSession
        profileSession = ProfileSession('profiled-task-%s' % task.getName(), Functor(profileInfo.taskFunc, *profileInfo.taskArgs))
        ret = profileSession.run()
        profileInfo.session = profileSession
        profileInfo.profiled = True
        return ret

    
    def _hasProfiledDesignatedTask(self):
        return self._taskProfileInfo.profiled

    
    def _getLastTaskProfileSession(self):
        return self._taskProfileInfo.session

    
    def _getRandomTask(self):
        now = globalClock.getFrameTime()
        avgFrameRate = globalClock.getAverageFrameRate()
        if avgFrameRate < 1.0000000000000001e-005:
            avgFrameDur = 0.0
        else:
            avgFrameDur = 1.0 / globalClock.getAverageFrameRate()
        next = now + avgFrameDur
        tasks = self.mgr.getTasks()
        i = random.randrange(tasks.getNumTasks())
        task = tasks.getTask(i)
        while not isinstance(task, PythonTask) or task.getWakeTime() > next:
            tasks.removeTask(i)
            i = random.randrange(tasks.getNumTasks())
            task = tasks.getTask(i)
        return task

    
    def __repr__(self):
        return str(self.mgr)

    
    def doYield(self, frameStartTime, nextScheduledTaskTime):
        pass

    
    def _runTests(self):
        pass


