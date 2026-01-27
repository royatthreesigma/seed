"use client";

import { type LucideIcon } from "lucide-react";
import type React from "react";

import { SidebarGroup, SidebarGroupLabel, SidebarMenu, SidebarMenuButton, SidebarMenuItem, useSidebar } from "@/components/ui/sidebar";

export function NavSection({
	options,
	title,
	children,
}: {
	options: {
		name: string;
		url: string;
		icon: LucideIcon | React.ComponentType<any>;
		newTab?: boolean;
	}[];
	title?: string;
	children?: React.ReactNode;
}) {
	return (
		<SidebarGroup>
			{title && <SidebarGroupLabel>{title}</SidebarGroupLabel>}
			<SidebarMenu>
				{options.map((item) => (
                    <SidebarMenuItem key={item.name}>
						<SidebarMenuButton asChild>
							<a href={item.url} target={item.newTab ? "_blank" : "_self"} rel={item.newTab ? "noopener noreferrer" : undefined} className="flex items-center gap-2 w-full">
								<item.icon />
								<span>{item.name}</span>
							</a>
						</SidebarMenuButton>
					</SidebarMenuItem>
				))}
                {children}
			</SidebarMenu>
		</SidebarGroup>
	);
}
