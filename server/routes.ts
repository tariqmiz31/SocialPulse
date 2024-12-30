app.post("/api/posts", async (req, res) => {
    try {
      const { content, platforms } = req.body;
      if (!content || !platforms || !Array.isArray(platforms)) {
        return res.status(400).json({ error: "Invalid request body" });
      }
    } catch (error) {
      console.error("Error processing request:", error);
      return res.status(500).json({ error: "Internal server error" });
    }
});