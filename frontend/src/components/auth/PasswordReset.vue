<template>

    <v-card>
        <v-card-title primary-title>
            <div>
                <h3 class="headline mb-0">New Password</h3>
                <p> Enter new password. </p>
            </div>
        </v-card-title>
        <v-card-text>

            <v-form
                    onSubmit="return false;"
            >
                <v-text-field v-on:keyup.enter="reset_password" prepend-icon="fas fa-envelope"  :error="password_warnings.length > 0" :error-messages="password_warnings" v-model="password" name="password" label="Password" type="password"></v-text-field>

            </v-form>

        </v-card-text>
        <v-card-actions>
            <v-alert :value="alertShow"  type="success" >
                {{message}}
            </v-alert>
            <v-alert :value="key_warnings_show"  type="error" >
                {{key_warnings}}
            </v-alert>
            <v-spacer></v-spacer>
            <v-btn color="primary" v-on:click="reset_password" >submit</v-btn>
        </v-card-actions>

    </v-card>
</template>

<script>
    import axios from 'axios'

    export default {
        name: "Verification",
        data(){
            return {
                warnings:{},
                password : "",
                message:[],
                alertShow:false

            }
        },

        computed: {
            key_warnings(){
                if (this.key_warnings_show){
                    return this.warnings["key"]
                }
                else {
                    return []
                }
            },
            password_warnings(){
                if ("password" in this.warnings){
                    return this.warnings["password"]
                }
                else {
                    return []
                }
            },
            key_warnings_show(){
                return "key" in this.warnings
            },


            reset_key() {
                return this.$route.params.id;

            },



        },
        methods: {
            reset_password: function(){
                // reset store
                // reset warnings
                this.warnings = {};
                this.alertShow = false;

                const payload = {"key":this.reset_key, password:this.password};

                axios.post(this.$store.state.endpoints.password_reset, payload)
                    .then(()=>{
                    })
                    .catch((error)=>{
                        this.warnings = error.response.data;
                    })
                    .finally(() => {
                        if(Object.keys(this.warnings).length === 0){
                            this.alertShow = true;
                            this.message = "Successful password reset. You can now login with your new password"
                        }
                    });
            }
        },

    }
</script>

<style scoped>
</style>