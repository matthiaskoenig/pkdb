<template>
    <div>

        <div v-if="user">
            <button v-on:click="logout">Logout</button>
        </div>
        <div v-else>
            <input type="text" placeholder="username" v-model="username">
            <input type="password" placeholder="password" v-model="password">
            <button v-on:click="login">Login</button>
        </div>
        <p>
            <span v-if="user">
            User: {{ user }}<br />
            Token: {{ token }}<br />
            </span>
            <span v-if="warnings">Warnings: {{ warnings }}</span>
        </p>
    </div>
</template>

<script>
    import axios from 'axios'

    export default {
        name: "UserLogin",
        data: function(){
            return {
                username: null,
                password: null,
                warnings: null
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
                // reset store
                this.logout();
                // reset warnings
                this.warnings = null;

                // window.alert("login id: " + this.username + "\n" + "password: " + this.password);
                const payload = {"username": this.username, "password": this.password};
                // console.log(payload);

                axios.post(this.$store.state.endpoints.obtainAuthToken, payload)
                    .then((response)=>{
                        this.$store.dispatch('login', {
                            username: this.username,
                            token: response.data.token
                        })
                    })
                    .catch((error)=>{
                        this.warnings = error.response.data;

                        console.log(error);
                    })
            },

            logout: function(){
                // window.alert("logout id: " + this.username);
                this.$store.dispatch('logout')
            }
        }
    }
</script>

<style scoped>
</style>