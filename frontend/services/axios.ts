import axios from "axios";

// Axios instance setup (normal/default)
const axiosInstance = axios.create({
	baseURL: process.env.NEXT_PUBLIC_API_URL,
});

// Add a request interceptor (include auth token if available)
axiosInstance.interceptors.request.use(
	async (config) => {
		/**
         * NOTE: you can include your auth logic here to get the token
         * For example, if you're using Firebase Authentication:
         const user = await new Promise<User | null>((resolve) => {
			const unsubscribe = onAuthStateChanged(auth, (user) => {
				unsubscribe(); // Unsubscribe from state change listener
				resolve(user); // Return the user object
			});
		});

		if (user) {
			const token = await user.getIdToken(); // Get Firebase token
			config.headers.Authorization = `Bearer ${token}`; // Add token to headers
		}
        */

		return config;
	},
	(error) => {
		return Promise.reject(error);
	}
);

export default axiosInstance;
