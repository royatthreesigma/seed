import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Toaster } from "@/components/ui/sonner";
// import { ClerkProvider, SignIn, SignInButton, SignUpButton, SignedIn, SignedOut, UserButton } from "@clerk/nextjs";
// import { AxiosAuthProvider } from "@/lib/axios";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { DefaultAppSidebar } from "@/components/sidebar/default/app-sidebar";
import "./globals.css";

const geistSans = Geist({
	variable: "--font-geist-sans",
	subsets: ["latin"],
});

const geistMono = Geist_Mono({
	variable: "--font-geist-mono",
	subsets: ["latin"],
});

export const metadata: Metadata = {
	title: "Built with Shippable",
	description: "Vibe code B2B apps that go beyond demo and into production",
};

export default function RootLayout({
	children,
}: Readonly<{
	children: React.ReactNode;
}>) {
	return (
		// <ClerkProvider>
		<html lang="en">
			<body
				className={`${geistSans.variable} ${geistMono.variable} antialiased h-screen flex flex-col overflow-hidden`}
				// `h-screen flex flex-col overflow-hidden` is to ensure full height for the layout and allow childrend to manage their own scrolling
			>
				<main className="flex-1 min-h-0 min-w-0">
					{/* <SignedOut>
							<div className="w-full h-full bg-blue-300 flex items-center justify-center">
								<SignIn routing="hash" />
							</div>
						</SignedOut> */}
					<SidebarProvider>
						<DefaultAppSidebar />
						<SidebarInset>{children}</SidebarInset>
					</SidebarProvider>
					{/* <SignedIn> */}
					{/* <AxiosAuthProvider> */}
					<SidebarProvider>
						<DefaultAppSidebar />
						<SidebarInset>{children}</SidebarInset>
					</SidebarProvider>
					{/* </AxiosAuthProvider> */}
					{/* </SignedIn> */}
				</main>
				<Toaster position="bottom-right" />
			</body>
		</html>
		// </ClerkProvider>
	);
}
