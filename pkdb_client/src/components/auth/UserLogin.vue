<template>
    <div>
        <input type="text" placeholder="username" v-model="username">
        <input type="password" placeholder="password" v-model="password">
        <button v-on:click="login">Login</button>
        <button v-on:click="logout">Logout</button>
        <p>Username: {{ username }}</p>
        <p>Token: {{ token }}</p>
    </div>
</template>

<script>
    export default {
        name: "UserLogin",
        data: function(){
            return {
                username: '',
                password: ''
            }
        },
        computed: {
            token() {
                return this.$store.state.token;
            },
            user() {
                return this.$store.state.username;
            },
        },
        methods: {
            login: function(){
                // window.alert("login id:" + this.username + "\n" + "password:" + this.password);
                // this.$store.
                this.$store.dispatch('login', {
                    username: this.username,
                    password: this.password
                })
            },
            logout: function(){
                //window.alert("logout id:" + this.username);
                this.$store.dispatch('logout')
            }
        }
    }
</script>

<style scoped>
</style>