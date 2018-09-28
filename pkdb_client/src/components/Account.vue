<template>
    <div>
    <h1>User Account</h1>
    <ul>
        <li><a :href="domain+'/accounts/signup/'">signup</a></li>
        <li><a :href="domain+'/accounts/login/'">login</a></li>
        <li><a :href="domain+'/accounts/logout/'">logout</a></li>
        <li><a :href="domain+'/accounts/password/change/'">change password</a></li>
        <li><a :href="domain+'/accounts/password/reset/'">reset password</a></li>
    </ul>
    </div>
</template>

<script>
    export default {
        name: "Accounts",
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