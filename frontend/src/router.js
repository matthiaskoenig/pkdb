import Vue from 'vue';
import Router from 'vue-router';

/* Home */
import Home from './components/Home';

/* TableViews */
import Studies from './components/Studies';
import Groups from './components/Groups';
import Individuals from './components/Individuals';
import Interventions from './components/Interventions';
import Outputs from './components/Outputs';
import Timecourses from './components/Timecourses';
import References from './components/References';

/* DetailViews */
import Study from './components/Study';
import Group from './components/Group';
import Individual from './components/Individual';
import Intervention from './components/Intervention';
import Output from './components/Output';
import Timecourse from './components/Timecourse';
import Reference from './components/Reference';

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
  // mode: 'history',
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
          path:"/studies/:id",
          name:"Study",
          component:Study,
          props: true
      },
      {
          path:"/groups/:id",
          name:"Group",
          component:Group,
          props: true
      },
      {
          path:"/individuals/:id",
          name:"Individual",
          component:Individual,
          props: true
      },
      {
          path:"/interventions/:id",
          name:"Intervention",
          component:Intervention,
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
          path: '/404',
          name: '404',
          component: Page404
      },
      {
          path: '*',
          redirect: '/404'
      },
  ],
    scrollBehavior (to, from, savedPosition) {
        return { x: 0, y: 0 }
    }

})
