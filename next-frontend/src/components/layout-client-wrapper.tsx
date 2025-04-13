"use client";

import React, { useState } from "react";
import { SidebarNav } from "@/components/sidebar-nav";
import { Button } from "@/components/ui/button";
import { Drawer, DrawerContent, DrawerTrigger } from "@/components/ui/drawer";
import { Menu } from "lucide-react";

export function LayoutClientWrapper({
  children,
}: {
  children: React.ReactNode;
}) {
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      {/* Mobile Header with Drawer Trigger */}
      <header className="sticky top-0 z-10 flex h-14 items-center justify-between border-b bg-background px-4 md:hidden">
        <span className="font-semibold">Stencil Search</span>
        <Drawer open={isDrawerOpen} onOpenChange={setIsDrawerOpen}>
          <DrawerTrigger asChild>
            <Button variant="outline" size="icon">
              <Menu className="h-5 w-5" />
              <span className="sr-only">Toggle Menu</span>
            </Button>
          </DrawerTrigger>
          <DrawerContent>
            <div className="p-4">
              <SidebarNav setIsDrawerOpen={setIsDrawerOpen} />
            </div>
          </DrawerContent>
        </Drawer>
      </header>

      {/* Sidebar for Desktop */}
      <aside className="w-64 hidden md:block border-r">
        <SidebarNav />
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 p-4 md:p-6">{children}</main>
    </div>
  );
} 