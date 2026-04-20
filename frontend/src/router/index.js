import { createRouter, createWebHistory } from 'vue-router'

const routes = [
    {
        path: '/',
        redirect: '/login'
    },
    {
        path: '/login',
        name: 'Login',
        component: () => import('../views/LoginView.vue')
    },
    {
        path: '/register',
        name: 'Register',
        component: () => import('../views/RegisterView.vue')
    },
    {
        path: '/home',
        name: 'Home',
        component: () => import('../views/HomeView.vue')
    },
    {
        path: '/parking',
        name: 'Parking',
        component: () => import('../views/ParkingView.vue')
    },
    {
        path: '/billing',
        name: 'Billing',
        component: () => import('../views/BillingView.vue')
    },
    {
        path: '/profile',
        name: 'Profile',
        component: () => import('../views/ProfileView.vue')
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

// Navigation Guard for Auth
router.beforeEach((to, from, next) => {
    const token = localStorage.getItem('token')
    const publicPages = ['/login', '/register']
    const authRequired = !publicPages.includes(to.path)

    if (authRequired && !token) {
        return next('/login')
    }
    next()
})

export default router
