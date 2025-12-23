export async function POST(req: Request) {
    const { question } = await req.json();
  
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_BACKEND_URL}/chat`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question })
      }
    );
  
    const data = await response.json();
    return Response.json(data);
  }
  