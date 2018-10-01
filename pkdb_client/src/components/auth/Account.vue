<template>
    <div>
        <h1>User Account</h1>
    <h2>Vue login</h2>
    <div id="login-example">
        <UserLogin></UserLogin>
        <CountTable></CountTable>
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

    </div>
</template>

<script>
    import UserLogin from '@/components/auth/UserLogin'

    export default {
        name: "Account",
        components: {
            UserLogin
        },
        props: {
            domain: String
        },
        data() {
            return {}
        },
        computed: {
            user() {
                return this.$store.state.username;
            },
        },
    }
</script>

<style scoped>

</style>