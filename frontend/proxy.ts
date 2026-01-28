/**
 * NOTE: Uncomment the following lines to enable Clerk middleware
 *
import { clerkMiddleware } from "@clerk/nextjs/server";
export default clerkMiddleware();
 *  
 */

// NOTE: The following is a placeholder middleware when you are not
// using Clerk. You can replace its logic with your own custom middleware
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Placeholder middleware - replace with your custom logic
export default function middleware(request: NextRequest) {
	// Add your custom middleware logic here
	return NextResponse.next();
}

export const config = {
	matcher: [
		// Skip Next.js internals and all static files, unless found in search params
		"/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
		// Always run for API routes
		"/(api|trpc)(.*)",
	],
};
