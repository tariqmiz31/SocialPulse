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
import { Plus, Calendar as CalendarIcon, Loader2, Settings } from "lucide-react";
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
  platformSettings: z.record(z.object({
    hashtags: z.string().optional(),
    targetAudience: z.string().optional(),
    postType: z.string().optional(),
  })).optional(),
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
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([]);

  const form = useForm<Task>({
    resolver: zodResolver(taskSchema),
    defaultValues: {
      title: "",
      description: "",
      content: "",
      platformIds: [],
      platformSettings: {},
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

  const handlePlatformSelect = (platformId: string) => {
    const currentPlatforms = form.getValues("platformIds") || [];
    const newPlatforms = currentPlatforms.includes(platformId)
      ? currentPlatforms.filter(id => id !== platformId)
      : [...currentPlatforms, platformId];

    form.setValue("platformIds", newPlatforms);
    setSelectedPlatforms(newPlatforms);
  };

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
            <DialogContent className="sm:max-w-[600px]">
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
                    <div className="flex flex-wrap gap-2">
                      {platforms?.map((platform) => (
                        <Button
                          key={platform.id}
                          type="button"
                          variant={selectedPlatforms.includes(platform.id.toString()) ? "default" : "outline"}
                          onClick={() => handlePlatformSelect(platform.id.toString())}
                        >
                          {platform.name}
                        </Button>
                      ))}
                    </div>
                    {form.formState.errors.platformIds && (
                      <p className="text-sm text-destructive">
                        {form.formState.errors.platformIds.message}
                      </p>
                    )}
                  </div>

                  {selectedPlatforms.map((platformId) => {
                    const platform = platforms?.find(p => p.id.toString() === platformId);
                    if (!platform) return null;

                    return (
                      <Card key={platformId} className="p-4">
                        <h3 className="font-semibold mb-2">إعدادات {platform.name}</h3>
                        <div className="space-y-2">
                          <div>
                            <label className="text-sm">الهاشتاغات</label>
                            <Input
                              {...form.register(`platformSettings.${platformId}.hashtags`)}
                              placeholder="مثال: #تسويق #اعمال"
                            />
                          </div>
                          <div>
                            <label className="text-sm">الجمهور المستهدف</label>
                            <Select
                              onValueChange={(value) =>
                                form.setValue(`platformSettings.${platformId}.targetAudience`, value)
                              }
                            >
                              <SelectTrigger>
                                <SelectValue placeholder="اختر الجمهور المستهدف" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="general">عام</SelectItem>
                                <SelectItem value="business">رجال أعمال</SelectItem>
                                <SelectItem value="youth">شباب</SelectItem>
                                <SelectItem value="professionals">محترفين</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          <div>
                            <label className="text-sm">نوع المنشور</label>
                            <Select
                              onValueChange={(value) =>
                                form.setValue(`platformSettings.${platformId}.postType`, value)
                              }
                            >
                              <SelectTrigger>
                                <SelectValue placeholder="اختر نوع المنشور" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="text">نص</SelectItem>
                                <SelectItem value="image">صورة</SelectItem>
                                <SelectItem value="video">فيديو</SelectItem>
                                <SelectItem value="link">رابط</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        </div>
                      </Card>
                    );
                  })}

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
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <h3 className="font-semibold mb-2">{task.title}</h3>
                        <p className="text-sm text-muted-foreground">
                          {task.description}
                        </p>
                      </div>
                      <Button variant="ghost" size="icon">
                        <Settings className="h-4 w-4" />
                      </Button>
                    </div>
                    <div className="flex flex-wrap gap-2 mb-4">
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
                    <div className="flex justify-between items-center text-sm text-muted-foreground">
                      <div className="flex items-center gap-2">
                        <CalendarIcon className="h-4 w-4" />
                        <span>
                          {format(new Date(task.scheduledTime), "PPP", {
                            locale: ar,
                          })}
                        </span>
                      </div>
                      <span className="capitalize">
                        {task.status === "draft"
                          ? "مسودة"
                          : task.status === "scheduled"
                          ? "مجدول"
                          : task.status === "published"
                          ? "منشور"
                          : "فشل"}
                      </span>
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