<template>
    <div>
        <h1>User Account</h1>
    <h2>Vue login</h2>
    <div id="login-example">
        <UserLogin></UserLogin>
    </div>


        <h2>Django endpoints</h2>
        <ul>
        <li><a :href="domain+'/accounts/signup/'">signup</a></li>
            <!-- not needed for anything
        <li><a :href="domain+'/accounts/login/'">login</a></li>
        <li><a :href="domain+'/accounts/logout/'">logout</a></li>
        -->
        <li><a :href="domain+'/accounts/password/change/'">change password</a></li>
        <li><a :href="domain+'/accounts/password/reset/'">reset password</a></li>
        </ul>

    </div>
</template>

<script>
    import UserLogin from './UserLogin'

    export default {
        name: "Accounts",
        components: {
            'UserLogin': UserLogin
        },
        props: {
            domain: String
        },
        data() {
            return {}
        }
    }
</script>

<style scoped>

</style>