import React, { useEffect, useState, useRef } from 'react';
import { cloneDeep } from 'lodash';
import { useNavigate } from 'react-router-dom';
import { useQuery, keepPreviousData, useMutation, useQueryClient } from '@tanstack/react-query';
import { EventApi, EventClickArg, EventDropArg } from '@fullcalendar/core';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import dayjs from 'dayjs';
import CustomParseFormatPlugin from 'dayjs/plugin/customParseFormat';

import Task from './Task/Task';
import { TasksViewProps } from '../../types';
import { ApiClient, TaskType } from '../../../../../api';
import './CalendarViewStyles.css';
import { useNotify } from '../../../../../contexts/notifications/notifications';

dayjs.extend(CustomParseFormatPlugin);

const CalendarView: React.FC<TasksViewProps> = ({ boardId, scope, siteId, companyId, searchTerm, module }) => {
  const notify = useNotify();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [events, setEvents] = useState<any>();
  const previousEventInfo = useRef<any>(null);

  const { data: taskData, isLoading: isLoadingTaskData } = useQuery({
    queryFn: async () => {
      return ApiClient.taskManagement.getTasks(boardId, {
        skip: 0,
        limit: 1000,
        ...(searchTerm && { search: searchTerm })
      });
    },
    queryKey: ['tasks', { boardId, searchTerm }],
    placeholderData: keepPreviousData
  });

  const { mutateAsync: updateTask } = useMutation({
    mutationFn: (args: any) => ApiClient.taskManagement.updateTask(args.boardId, args.taskId, args.data)
  });

  const createCalendarEvents = (tasks: TaskType[]) => {
    const calendarEvents = tasks.map((task: TaskType) => ({
      id: task.id,
      title: task.name,
      start: task.due_date,
      allDay: true,
      extendedProps: {
        description: task.description,
        priority: task.priority,
        due_date: task.due_date,
        id: task.id,
        externalId: task.external_id,
        creator: task.creator,
        assignee: task.assignee,
        status: task.status
      }
    }));

    setEvents(cloneDeep(calendarEvents));
  };

  const updateTaskDetails = async (details: EventApi) => {
    if (!details) return null;

    const { id, title, startStr, extendedProps } = details;

    try {
      await updateTask({
        boardId: boardId,
        taskId: id,
        data: {
          assignee_id: extendedProps.assignee?.id || null,
          name: title,
          priority: extendedProps.priority,
          due_date: startStr,
          status_id: extendedProps.status?.id || null
        }
      });

      const updatedEvents = events.map((evt: any) =>
        evt.id === parseInt(details.id)
          ? {
              ...evt,
              start: dayjs(details.start).format('YYYY-MM-DD')
            }
          : evt
      );

      setEvents(updatedEvents);
      notify(`Task ${extendedProps.externalId} was updated`);
    } catch (e: any) {
      notify(e.response?.data?.message || 'Something went wrong with moving task...');
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    }
  };

  const handleEventDrop = (info: EventDropArg) => {
    const { event } = info;
    const today = dayjs().startOf('day');
    const newStart = dayjs(event.start).startOf('day');

    if (newStart.isBefore(today)) {
      info.revert();
      notify('Due date cannot be earlier than the current date.');
    } else {
      updateTaskDetails(event);
    }
  };

  const handleEventDragStart = (info: any) => {
    const { event } = info;
    previousEventInfo.current = {
      start: event.start
    };
  };

  const handleEventClick = React.useCallback(
    (eventInfo: EventClickArg) => {
      if (eventInfo?.event?.id) {
        if (module === 'O&M') {
          if (scope === 'site') {
            navigate(`/operations-and-maintenance/companies/${companyId}/sites/${siteId}/tasks/${eventInfo.event.id}`);
            return;
          }
          navigate(`/operations-and-maintenance/companies/${companyId}/tasks/${eventInfo.event.id}`);
          return;
        }
        if (scope === 'site') {
          navigate(`/asset-management/companies/${companyId}/sites/${siteId}/tasks/${eventInfo.event.id}`);
        } else {
          navigate(`/asset-management/companies/${companyId}/tasks/${eventInfo.event.id}`);
        }
      }
    },
    [navigate, companyId, siteId, scope]
  );

  useEffect(() => {
    if (!isLoadingTaskData && taskData) {
      createCalendarEvents(taskData.items);
    }
  }, [isLoadingTaskData, taskData, searchTerm]);

  if (isLoadingTaskData || !taskData) return null;

  return (
    <div className="calendar-container">
      <FullCalendar
        plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
        initialView="timeGridWeek"
        editable={true}
        selectable={true}
        droppable={true}
        eventDrop={handleEventDrop}
        eventDragStart={handleEventDragStart}
        eventClick={handleEventClick}
        headerToolbar={{
          left: 'prev,next today',
          center: 'title',
          right: 'dayGridMonth,timeGridWeek'
        }}
        slotEventOverlap={false}
        events={events}
        eventResizableFromStart={false}
        eventDurationEditable={false}
        moreLinkClick="popover"
        eventContent={(eventInfo: any) => <Task eventInfo={eventInfo} />}
        height="auto"
        views={{
          dayGridMonth: {
            dayMaxEvents: 3
          },
          timeGridWeek: {
            dayMaxEvents: false,
            allDaySlot: true,
            slotMinTime: '24:00:00',
            slotMaxTime: '24:00:00'
          }
        }}
      />
    </div>
  );
};

export default CalendarView;
