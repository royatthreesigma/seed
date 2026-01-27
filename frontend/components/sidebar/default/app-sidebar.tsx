"use client";

import * as React from "react";
import { BookOpen, Bot, Command, Frame, Home, LifeBuoy, Map, PieChart, Search, Send, Settings2, SquareTerminal } from "lucide-react";

import { Sidebar, SidebarContent, SidebarFooter, SidebarHeader, SidebarMenu, SidebarMenuButton, SidebarMenuItem, SidebarTrigger } from "@/components/ui/sidebar";
// import { UserButton, useUser } from "@clerk/nextjs";
import { NavSection } from "./nav-section";
import { ActionSearch } from "./action-search";

const data = {
	navMain: [
		{
			name: "Home",
			url: "/",
			icon: Home,
		},
	],
	navSecondary: [],
	resources: [
		{
			name: "Documentation",
			url: "#",
			icon: BookOpen,
		},
	],
};

export function DefaultAppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
	// const { user } = useUser();

	return (
		<Sidebar collapsible="icon" {...props}>
			<SidebarHeader>
				<SidebarMenu>
					<SidebarMenuItem className="flex items-center">
						<SidebarMenuButton size="lg" asChild className="group-data-[collapsible=icon]:hidden">
							<a href="/">
								<div className="bg-sidebar-primary text-sidebar-primary-foreground flex aspect-square size-8 items-center justify-center rounded-lg">
									<Command className="size-4" />
								</div>
								<div className="grid flex-1 text-left text-sm leading-tight">
									<span className="truncate font-medium">Banana Inc</span>
									<span className="truncate text-xs">Enterprise</span>
								</div>
							</a>
						</SidebarMenuButton>
						<SidebarTrigger className="ml-auto" />
					</SidebarMenuItem>
				</SidebarMenu>
			</SidebarHeader>
			<SidebarContent>
				<NavSection options={data.navMain}>
					<ActionSearch />
				</NavSection>
				<NavSection options={data.resources} title="Resources" />
			</SidebarContent>
			<SidebarFooter>
				{/* Uncomment if using Clerk Auth */}
				{/* <div className="w-full flex items-center gap-2 px-1 py-1.5 text-left text-sm">
					<UserButton />
					{user && (
						<div className="flex flex-col overflow-hidden">
							<span className="truncate font-semibold">{user.fullName || user.username}</span>
							<span className="truncate text-xs text-muted-foreground">{user.primaryEmailAddress?.emailAddress}</span>
						</div>
					)}
				</div> */}
			</SidebarFooter>
		</Sidebar>
	);
}
