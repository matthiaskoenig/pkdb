<template>
    <div id="page404">
        <h1>404</h1>
        <p>
            Page <strong v-if="this.prevRoute">{{ this.prevRoute.path }}</strong> not found or no access to information as user
            <strong v-if="this.$store.state.username">{{ this.$store.state.username }}</strong>
            <strong v-if="!this.$store.state.username">anonymous</strong>.
        </p>
        <p>
            Please try to login or change user to access the page.
        </p>
        <p>
            <user-login ></user-login>
        </p>
    </div>
</template>

<script>
    import UserLogin from './auth/UserLogin'
    export default {
        name: 'Page404',
        components: {
            UserLogin
        },
        data() {
            return {
                prevRoute: null
            }
        },
        beforeRouteEnter(to, from, next) {
            next(vm => {
                vm.prevRoute = from
            })
        },
        methods: {
        }
    }
</script>

<style>
</style>