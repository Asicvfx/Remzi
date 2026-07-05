import "./globals.css";

export const metadata = {
  title: "Remzi Workspace",
  description: "Ask questions about your documents with Remzi.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
