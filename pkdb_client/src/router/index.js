import Vue from 'vue'
import Router from 'vue-router'
import App from '@/App'
import Home from '@/components/Home'
import About from '@/components/About'
import Contact from '@/components/Contact'

Vue.use(Router)

export default new Router({
    routes: [
        {
            path: '/home',
            name: 'Home',
            component: Home
        },
        {
            path: '/about',
            name: 'About',
            component: About
        },
        {
            path: '/contact',
            name: 'Contact',
            component: Contact
        },
    ]
})