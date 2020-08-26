import Vue from 'vue';
import Router from 'vue-router';

import Home from './components/Home';
import Data from './components/Data';
import Results from './components/Results'
import Search from './components/Search';
import Page404 from './components/Page404';
import Curation from './components/Curation';
import Account from './components/auth/Account';
import Registration from './components/auth/Registration';
import Verification from './components/auth/Verification';
import RequestPasswordReset from './components/auth/RequestPasswordReset';
import PasswordReset from './components/auth/PasswordReset';


Vue.use(Router);

export default new Router({
    mode: 'history',
    routes: [
        {
            path: '/',
            name: 'Home',
            component: Home
        },
        {
            path: '/search',
            name: 'Search',
            component: Search
        },
        {
            path: '/data',
            name: 'Data',
            component: Data
        },
        {
            path: '/results',
            name: 'Results',
            component: Results
        },
        {
            path: '/curation',
            name: 'Curation',
            component: Curation
        },
        {
            path: '/account',
            name: 'Account',
            component: Account
        },
        {
            path: '/verification/:id',
            name: 'Verification',
            component: Verification,
            props: true
        },
        {
            path: '/registration',
            name: 'Registration',
            component: Registration
        },
        {
            path: '/request-password-reset',
            name: 'RequestPasswordReset',
            component: RequestPasswordReset
        },
        {
            path: '/reset-password/:id',
            name: 'PasswordReset',
            component: PasswordReset,
        },
        {
            path: '/404',
            name: '404',
            component: Page404
        },
        {
            path: '*',
            redirect: '/404'
        },
        /*
        {
            path: '/studies',
            name: 'Studies',
            component: Studies
        },
        {
            path: "/studies/:id",
            name: "Study",
            component: Study,
            props: true
        },
        */

    ],
})
