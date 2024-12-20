import { useState } from "react";
import { Calendar as CalendarComponent } from "@/components/ui/calendar";
import { Card, CardContent } from "@/components/ui/card";
import { DragDropContext, Droppable, Draggable } from "react-beautiful-dnd";
import { useQuery } from "@tanstack/react-query";
import type { ScheduledPost } from "@/lib/types";

export default function Calendar() {
  const [date, setDate] = useState<Date | undefined>(new Date());
  
  const { data: scheduledPosts } = useQuery<ScheduledPost[]>({
    queryKey: ["/api/scheduled-posts"],
  });

  const onDragEnd = (result: any) => {
    // Handle drag and drop logic here
  };

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Content Calendar</h1>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardContent className="p-6">
            <CalendarComponent
              mode="single"
              selected={date}
              onSelect={setDate}
              className="rounded-md border"
            />
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <h2 className="text-xl font-semibold mb-4">Scheduled Posts</h2>
            <DragDropContext onDragEnd={onDragEnd}>
              <Droppable droppableId="scheduled-posts">
                {(provided) => (
                  <div {...provided.droppableProps} ref={provided.innerRef}>
                    {scheduledPosts?.map((post, index) => (
                      <Draggable key={post.id} draggableId={post.id} index={index}>
                        {(provided) => (
                          <div
                            ref={provided.innerRef}
                            {...provided.draggableProps}
                            {...provided.dragHandleProps}
                            className="p-4 mb-2 bg-card rounded-lg border"
                          >
                            <p className="font-medium">{post.content}</p>
                            <div className="flex gap-2 mt-2">
                              {post.platforms.map(platform => (
                                <span
                                  key={platform}
                                  className="text-xs px-2 py-1 rounded-full bg-primary/10"
                                >
                                  {platform}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </Draggable>
                    ))}
                    {provided.placeholder}
                  </div>
                )}
              </Droppable>
            </DragDropContext>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
