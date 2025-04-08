"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Home, Star, Layers, Activity, Settings } from "lucide-react";
import React from 'react'; // Import React

const navItems = [
  { href: "/", label: "Search", icon: Home },
  { href: "/favorites", label: "Favorites", icon: Star },
  { href: "/collections", label: "Collections", icon: Layers },
  { href: "/health", label: "Health", icon: Activity },
  { href: "/settings", label: "Settings", icon: Settings },
];

// Define props interface
interface SidebarNavProps {
  // Optional prop to close the drawer on mobile
  setIsDrawerOpen?: React.Dispatch<React.SetStateAction<boolean>>;
}

export function SidebarNav({ setIsDrawerOpen }: SidebarNavProps) { // Destructure the prop
  const pathname = usePathname();

  const handleLinkClick = () => {
    // Close the drawer if the function is provided (i.e., on mobile)
    setIsDrawerOpen?.(false);
  };

  return (
    <nav className="flex flex-col space-y-1 p-4 h-full"> {/* Removed border-r, handle in layout */}
      {navItems.map((item) => {
        const Icon = item.icon;
        return (
          // Add onClick to the Link to close the drawer
          <Link key={item.href} href={item.href} legacyBehavior passHref onClick={handleLinkClick}>
            <Button
              variant={pathname === item.href ? "secondary" : "ghost"}
              className={cn(
                "w-full justify-start",
                pathname === item.href && "font-semibold"
              )}
            >
              <Icon className="mr-2 h-4 w-4" />
              {item.label}
            </Button>
          </Link>
        );
      })}
    </nav>
  );
}