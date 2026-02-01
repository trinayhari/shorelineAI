"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface SearchResultsProps {
  answer: string | null;
  title?: string;
}

export function SearchResults({ answer, title = "Answer" }: SearchResultsProps) {
  if (!answer) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="prose prose-sm max-w-none dark:prose-invert">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{answer}</ReactMarkdown>
      </CardContent>
    </Card>
  );
}
