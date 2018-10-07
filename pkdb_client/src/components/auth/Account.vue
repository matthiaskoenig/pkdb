<template>
    <span>
        <h1>User Account</h1>
        <h2>Vue login</h2>
        <div id="login-example">
            <user-login></user-login>
        </div>

        <h2>Django endpoints</h2>
        <ul>
            <span v-if="user">
            <li><a :href="domain+'/accounts/password/change/'+user">change password</a></li>
            <li><a :href="domain+'/accounts/password/reset/'+user">reset password</a></li>
            </span>
            <span v-else>
                <li><a :href="domain+'/accounts/signup/'">signup</a></li>
                <!-- not needed for anything
                <li><a :href="domain+'/accounts/login/'">login</a></li>
                <li><a :href="domain+'/accounts/logout/'">logout</a></li>
                -->
            </span>
        </ul>
    </span>
</template>

<script>
    import UserLogin from './UserLogin'

    export default {
        name: "Account",
        components: {
            UserLogin
        },
        data() {
            return {}
        },
        computed: {
            domain() {
                return this.$store.state.django_domain;
            },
            user() {
                return this.$store.state.username;
            },
        },
    }
</script>

<style scoped>
</style>