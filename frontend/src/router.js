import Vue from 'vue';
import Router from 'vue-router';

/* Home */
import Home from './components/Home';

/* Search */
import Search from './components/Search';

/* TableViews */
import Studies from './components/Studies';
/*
import Groups from './components/deprecated/Groups';
import Individuals from './components/deprecated/Individuals';
import Interventions from './components/deprecated/Interventions';
import Outputs from './components/deprecated/Outputs';
import Timecourses from './components/deprecated/Timecourses';
import References from './components/deprecated/References';
*/


/* DetailViews */
import Study from './components/Study';
/*
import Group from './components/deprecated/Group';
import Individual from './components/deprecated/Individual';
import Intervention from './components/deprecated/Intervention';
import Output from './components/deprecated/Output';
import Timecourse from './components/deprecated/Timecourse';
import InfoNode from './components/InfoNode';
import Reference from './components/deprecated/Reference';
*/

/* 404 */
import Page404 from './components/Page404';

/* Curation */
import Curation from './components/Curation';

/* Account */
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
        {
            path: '/search',
            name: 'Search',
            component: Search
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
        /*{
            path: '/groups',
            name: 'Groups',
            component: Groups
        },
        {
            path: '/individuals',
            name: 'Individuals',
            component: Individuals
        },
        {
            path: '/interventions',
            name: 'Interventions',
            component: Interventions
        },
        {
            path: '/outputs',
            name: 'Outputs',
            component: Outputs
        },
        {
            path: '/timecourses',
            name: 'Timecourses',
            component: Timecourses
        },
        {
            path: '/references',
            name: 'References',
            component: References
        },
        {
            path: "/groups/:id",
            name: "Group",
            component: Group,
            props: true
        },
        {
            path: "/individuals/:id",
            name: "Individual",
            component: Individual,
            props: true
        },
        {
            path: "/interventions/:id",
            name: "Intervention",
            component: Intervention,
            props: true
        },
        {
            path: "/outputs/:id",
            name: "Output",
            component: Output,
            props: true
        },
        {
            path: "/timecourses/:id",
            name: "Timecourse",
            component: Timecourse,
            props: true
        },
        {
            path: "/references/:id",
            name: "Reference",
            component: Reference,
            props: true
        },
        {
            path: "/info_nodes/:id",
            name: "InfoNode",
            component: InfoNode,
            props: true
        },*/
    ],


})
