import "./globals.css";
import type { Metadata } from "next";
import { GeistSans, GeistMono } from "geist/font";
import { Providers } from "./providers";
import { SidebarNav } from "@/components/sidebar-nav";
import { ImportStatusIndicator } from "@/components/import-status";
import { Toaster } from "@/components/ui/sonner";
import { useState } from "react"; // Import useState
import { Button } from "@/components/ui/button"; // Import Button
import { Drawer, DrawerContent, DrawerTrigger } from "@/components/ui/drawer"; // Import Drawer components
import { Menu } from "lucide-react"; // Import Menu icon

// Initialize fonts
const geistSans = GeistSans;
const geistMono = GeistMono;
export const metadata: Metadata = {
  title: "Visio Stencil Search", // Updated title
  description: "Search and manage Visio stencils",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const [isDrawerOpen, setIsDrawerOpen] = useState(false); // State for drawer

  return (
    <html lang="en" suppressHydrationWarning> {/* Added suppressHydrationWarning for potential theme issues */}
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <Providers>
          <div className="flex min-h-screen flex-col md:flex-row"> {/* Ensure flex column on mobile */}

             {/* Mobile Header with Drawer Trigger */}
             <header className="sticky top-0 z-10 flex h-14 items-center justify-between border-b bg-background px-4 md:hidden">
                 <span className="font-semibold">Stencil Search</span> {/* Optional: Add title */}
                 <Drawer open={isDrawerOpen} onOpenChange={setIsDrawerOpen}>
                     <DrawerTrigger asChild>
                        <Button variant="outline" size="icon">
                           <Menu className="h-5 w-5" />
                           <span className="sr-only">Toggle Menu</span>
                        </Button>
                     </DrawerTrigger>
                     <DrawerContent> {/* Drawer content slides from the side */}
                         <div className="p-4"> {/* Add padding inside drawer */}
                            {/* Pass setter to close drawer on nav */}
                            <SidebarNav setIsDrawerOpen={setIsDrawerOpen} />
                         </div>
                     </DrawerContent>
                 </Drawer>
             </header>

            {/* Sidebar for Desktop */}
            <aside className="w-64 hidden md:block border-r">
              {/* No need to pass setter here */}
              <SidebarNav />
            </aside>

            {/* Main Content Area */}
            <main className="flex-1 p-4 md:p-6">
              {children}
            </main>
          </div>
          <ImportStatusIndicator />
          <Toaster />
        </Providers>
      </body>
    </html>
  );
}
