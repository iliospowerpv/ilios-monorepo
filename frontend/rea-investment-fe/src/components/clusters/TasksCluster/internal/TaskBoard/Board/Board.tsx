import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DragDropContext, Droppable } from 'react-beautiful-dnd';

import Task from '../Task/Task';
import { BoardContainer, ColumnHeader, Title, TaskList, Column } from '../TaskBoard.styles';
import { TaskType } from '../../../../../../api';

const Board: React.FC<any> = ({ data, scope, siteId, companyId, setDragDetails, module }) => {
  const navigate = useNavigate();
  const [columns, setColumns] = useState(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleDragStart = () => {
    setIsDragging(true);
  };

  const handleDragEnd = (result: any, columns: any, setColumns: any) => {
    if (!result.destination) return;

    const { source, destination, draggableId } = result;

    if (source.droppableId === destination.droppableId && source.index === destination.index) return;

    if (source.droppableId !== destination.droppableId) {
      const sourceColumn = columns[source.droppableId];
      const destColumn = columns[destination.droppableId];
      const sourceItems = [...sourceColumn.items];
      const destItems = [...destColumn.items];
      const [removed] = sourceItems.splice(source.index, 1);

      destItems.splice(destination.index, 0, removed);
      setColumns({
        ...columns,
        [source.droppableId]: {
          ...sourceColumn,
          items: sourceItems
        },
        [destination.droppableId]: {
          ...destColumn,
          items: destItems
        }
      });
    } else {
      const column = columns[source.droppableId];
      const copiedItems = [...column.items];
      const [removed] = copiedItems.splice(source.index, 1);

      copiedItems.splice(destination.index, 0, removed);
      setColumns({
        ...columns,
        [source.droppableId]: {
          ...column,
          items: copiedItems
        }
      });
    }

    setDragDetails({ taskId: +draggableId, statusId: +destination.droppableId });
    setIsDragging(false);
  };

  const onTaskClicked = React.useCallback(
    (id: number) => {
      if (!isDragging) {
        if (module === 'O&M') {
          scope === 'site'
            ? navigate(`/operations-and-maintenance/companies/${companyId}/sites/${siteId}/tasks/${id}`)
            : navigate(`/operations-and-maintenance/companies/${companyId}/tasks/${id}`);
          return;
        }
        if (scope === 'site') {
          navigate(`/asset-management/companies/${companyId}/sites/${siteId}/tasks/${id}`);
          return;
        }
        navigate(`/asset-management/companies/${companyId}/tasks/${id}`);
      }
    },
    [navigate, companyId, siteId, isDragging, scope]
  );

  useEffect(() => {
    setColumns(data);
  }, [data]);

  if (!columns) return null;

  return (
    <DragDropContext onDragStart={handleDragStart} onDragEnd={result => handleDragEnd(result, columns, setColumns)}>
      <BoardContainer>
        {Object.entries(columns).map(([columnId, column]: any, colIndex: number) => {
          return (
            <Droppable key={`column-${columnId}--index-${colIndex}`} droppableId={columnId}>
              {provided => (
                <Column>
                  <ColumnHeader>
                    <Title>{`${column.name} (${column?.items.length})`}</Title>
                  </ColumnHeader>
                  <TaskList ref={provided.innerRef} {...provided.droppableProps}>
                    {column.items.map((item: TaskType, index: number) => (
                      <Task
                        key={`task-${item?.id}--index-${index}`}
                        item={item}
                        index={index}
                        onTaskClick={onTaskClicked}
                      />
                    ))}
                    {provided.placeholder}
                  </TaskList>
                </Column>
              )}
            </Droppable>
          );
        })}
      </BoardContainer>
    </DragDropContext>
  );
};

export default Board;
