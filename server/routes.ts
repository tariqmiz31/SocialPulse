import { Application } from "express";

export function registerRoutes(app: Application) {
    app.post("/api/posts", async (req, res) => {
        try {
            const { content, platforms } = req.body;

            if (!content || !platforms || !Array.isArray(platforms)) {
                return res.status(400).json({
                    error: "Invalid request body",
                    message:
                        "Content and platforms are required, and platforms must be an array.",
                });
            }

            const post = await db
                .insert(posts)
                .values({
                    content,
                    platforms,
                    status: "pending",
                    scheduledFor: new Date(),
                })
                .returning();

            return res.status(201).json({
                message: "Post created successfully",
                post,
            });
        } catch (error) {
            console.error("Error processing request:", error);

            return res.status(500).json({
                error: "Internal server error",
                details:
                    process.env.NODE_ENV === "development"
                        ? error.message
                        : undefined,
            });
        }
    });
}
