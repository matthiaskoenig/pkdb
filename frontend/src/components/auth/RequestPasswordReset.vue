<template>
    <div>
        <v-card>
            <v-card-title primary-title>
            <div>
                <h3 class="headline mb-0">Request a Password Rest</h3>
                <p> Request a password reset for the user with the provided email address. A reset token will be generated and emailed to the user. </p>
                <div> * The provided email address must be verified.</div>
                <div> * The operation will appear successful even if no reset email is sent. This is done to avoid leaking email addresses.</div>
            </div>
            </v-card-title>
            <v-card-text>

                <v-form
                        onSubmit="return false;"
                >
                    <v-text-field v-on:keyup.enter="request_reset" prepend-icon="fas fa-envelope"  :error="email_warnings.length > 0" :error-messages="email_warnings" v-model="email" name="email" label="Email" type="text"></v-text-field>

                </v-form>

            </v-card-text>
            <v-card-actions>
                <v-alert :value="alertShow"  type="success" >
                {{message}}
                </v-alert>
                <v-spacer></v-spacer>
                <v-btn color="primary" v-on:click="request_reset" >request reset</v-btn>
            </v-card-actions>

        </v-card>

    </div>

</template>

<script>
    import axios from 'axios'

    export default {
        name: "RequestPasswordReset",
        data(){
            return {
                warnings:{},
                email : "",
                message:"",
                alertShow:false,
            }
        },
        computed:{
            email_warnings(){

                if ("email" in this.warnings){
                    return this.warnings["email"]
                }
                else {
                    return []
                }
            }
        },
        methods: {
            request_reset: function(){
                // reset store
                // reset warnings
                this.warnings = {};
                const payload = {"email":this.email.toLowerCase()};
                axios.post(this.$store.state.endpoints.request_password_reset, payload)
                    .then((response)=>{
                    })
                    .catch((error)=>{
                        this.warnings = error.response.data;
                    })
                    .finally(() =>{
                        if(Object.keys(this.warnings).length === 0){
                            this.alertShow = true;
                            this.message = "Successful request for password reset. Check your mails for the password reset link."
                    }
                    });
            }


        }
    }
</script>

<style scoped>
</style>