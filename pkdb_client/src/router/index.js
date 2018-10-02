import Vue from 'vue'
import Router from 'vue-router'

/* Home */
import Home from '@/components/Home'

/* TableViews */
import Studies from '@/components/Studies'
import Groups from '@/components/Groups'
import Individuals from '@/components/Individuals'
import Interventions from '@/components/Interventions'
import Outputs from '@/components/Outputs'
import Timecourses from '@/components/Timecourses'
import References from '@/components/References'

/* About */
import About from '@/components/About'

/* Account */
import Account from '@/components/auth/Account'

/* DetailViews */
import CharacteristicaDetail from '@/components/CharacteristicaDetail'
import GroupDetail from '@/components/GroupDetail'
import IndividualDetail from '@/components/IndividualDetail'
import StudyDetail from '@/components/StudyDetail'
import TimecourseDetail from '@/components/TimecourseDetail'


Vue.use(Router);

export default new Router({
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
            path:"/studies/:id",
            name:"StudyDetail",
            component:StudyDetail,
            props: true
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
            path: '/about',
            name: 'About',
            component: About
        },
        {
            path: '/account',
            name: 'Account',
            component: Account
        },

        {
            path:"/characteristica/:id",
            name:"CharacteristicaDetail",
            component:CharacteristicaDetail,
            props: true
        },
        {
            path:"/timecourse/:id",
            name:"TimecourseDetail",
            component:TimecourseDetail,
            props: true
        },
        {
            path:"/group/:id",
            name:"GroupDetail",
            component:GroupDetail,
            props: true
        },
        {
            path:"/individual/:id",
            name:"IndividualDetail",
            component:IndividualDetail,
            props: true
        }
    ]
})