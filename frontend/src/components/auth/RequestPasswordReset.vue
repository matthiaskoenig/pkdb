<template>
    <div>
        <v-card-text>
            <v-form>
                <v-text-field prepend-icon="fas fa-envelope"  :error="email_warnings.length" :error-messages="email_warnings" v-model="email" name="email" label="Email" type="text"></v-text-field>

            </v-form>
        </v-card-text>

        <v-alert :value="success"  type="success" >
            {{password_message}}
        </v-alert>

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
                verification_message:[],
                success:false

            }
        },

        methods: {
            verify: function(){
                // reset store
                // reset warnings
                this.warnings = {};
                this.success = false;

                const payload = {"key":this.verification_key};

                axios.post(this.$store.state.endpoints.verify, payload)
                    .then((response)=>{

                        this.email = response.data.email;
                        this.success = true

                    })
                    .catch((error)=>{
                        this.warnings = error.response.data;
                    })
                    .finally(() => {
                        this.password_message = this.verification_m();
                    });
            },
            verification_m(){
                if (this.email){
                    return ["A link to rest your password has been send to your email."]
                }
                if (this.key_warnings){
                    return this.key_warnings
                }
            }

        },
        beforeMount(){
            this.verify()
        },
    }
</script>

<style scoped>
</style>