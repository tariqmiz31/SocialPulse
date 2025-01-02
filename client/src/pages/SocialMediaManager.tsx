import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Calendar } from "@/components/ui/calendar";
import { Form } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Plus, Calendar as CalendarIcon, Loader2 } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { format } from "date-fns";
import { ar } from "date-fns/locale";

const taskSchema = z.object({
  title: z.string().min(1, "العنوان مطلوب"),
  description: z.string().optional(),
  content: z.string().min(1, "المحتوى مطلوب"),
  platformIds: z.array(z.string()).min(1, "يجب اختيار منصة واحدة على الأقل"),
  scheduledTime: z.date(),
});

type Task = z.infer<typeof taskSchema>;

type Platform = {
  id: number;
  name: string;
  active: boolean;
};

export default function SocialMediaManager() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [isAddTaskOpen, setIsAddTaskOpen] = useState(false);
  const [selectedDate, setSelectedDate] = useState<Date>();

  const form = useForm<Task>({
    resolver: zodResolver(taskSchema),
    defaultValues: {
      title: "",
      description: "",
      content: "",
      platformIds: [],
    },
  });

  const { data: platforms, isLoading: loadingPlatforms } = useQuery<Platform[]>({
    queryKey: ["/api/platforms"],
  });

  const { data: tasks, isLoading: loadingTasks } = useQuery({
    queryKey: ["/api/tasks"],
  });

  const createTask = useMutation({
    mutationFn: async (taskData: Task) => {
      const response = await fetch("/api/tasks", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify(taskData),
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/tasks"] });
      setIsAddTaskOpen(false);
      form.reset();
      toast({
        title: "نجاح",
        description: "تم إنشاء المهمة بنجاح",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "خطأ",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const onSubmit = (data: Task) => {
    createTask.mutate(data);
  };

  if (loadingPlatforms || loadingTasks) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>إدارة المحتوى الاجتماعي</CardTitle>
          <Dialog open={isAddTaskOpen} onOpenChange={setIsAddTaskOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 ml-2" />
                إضافة مهمة جديدة
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
              <DialogHeader>
                <DialogTitle>إضافة مهمة جديدة</DialogTitle>
              </DialogHeader>
              <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                  <div className="space-y-2">
                    <label>العنوان</label>
                    <Input {...form.register("title")} />
                    {form.formState.errors.title && (
                      <p className="text-sm text-destructive">
                        {form.formState.errors.title.message}
                      </p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <label>الوصف</label>
                    <Textarea {...form.register("description")} />
                  </div>

                  <div className="space-y-2">
                    <label>المحتوى</label>
                    <Textarea {...form.register("content")} />
                    {form.formState.errors.content && (
                      <p className="text-sm text-destructive">
                        {form.formState.errors.content.message}
                      </p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <label>المنصات</label>
                    <Select
                      onValueChange={(value) =>
                        form.setValue("platformIds", [value])
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="اختر المنصة" />
                      </SelectTrigger>
                      <SelectContent>
                        {platforms?.map((platform) => (
                          <SelectItem
                            key={platform.id}
                            value={platform.id.toString()}
                          >
                            {platform.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {form.formState.errors.platformIds && (
                      <p className="text-sm text-destructive">
                        {form.formState.errors.platformIds.message}
                      </p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <label>موعد النشر</label>
                    <div className="grid gap-2">
                      <Calendar
                        mode="single"
                        selected={selectedDate}
                        onSelect={(date) => {
                          setSelectedDate(date);
                          if (date) {
                            form.setValue("scheduledTime", date);
                          }
                        }}
                        locale={ar}
                      />
                    </div>
                  </div>

                  <Button type="submit" className="w-full">
                    {createTask.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      "إضافة"
                    )}
                  </Button>
                </form>
              </Form>
            </DialogContent>
          </Dialog>
        </CardHeader>
        <CardContent>
          {tasks?.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              لا توجد مهام حالياً
            </div>
          ) : (
            <div className="grid gap-4">
              {tasks?.map((task) => (
                <Card key={task.id}>
                  <CardContent className="pt-6">
                    <h3 className="font-semibold mb-2">{task.title}</h3>
                    <p className="text-sm text-muted-foreground mb-4">
                      {task.description}
                    </p>
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-2">
                        <CalendarIcon className="h-4 w-4" />
                        <span className="text-sm">
                          {format(new Date(task.scheduledTime), "PPP", {
                            locale: ar,
                          })}
                        </span>
                      </div>
                      <div className="flex gap-2">
                        {task.platformIds.map((platformId) => {
                          const platform = platforms?.find(
                            (p) => p.id === parseInt(platformId)
                          );
                          return (
                            <span
                              key={platformId}
                              className="px-2 py-1 rounded-full bg-primary/10 text-primary text-sm"
                            >
                              {platform?.name}
                            </span>
                          );
                        })}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
