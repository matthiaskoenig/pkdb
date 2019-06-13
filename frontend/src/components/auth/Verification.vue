<template>
    <div>
        <div v-if="success">
            {{verification_message}}
        </div>

    </div>


</template>

<script>
    import axios from 'axios'

    export default {
        name: "Verification",
        data(){
            return {
                warnings:{},
                email : "",
                success:false
            }
        },

        computed: {
            key_warnings(){
                if ("key_warnings" in this.warnings){
                    return this.warnings["key_warnings"]
                }
                else {
                    return []
                }
            },

            verification_key() {
                let path = this.$route.path;
                let tokens = path.split('/');
                return tokens[tokens.length - 1];
            },

            verification_message(){
                if (this.email){
                    return "Your email " + this.email + " has been verified. You can now login."
                }
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
                        this.email = response["email"];
                        this.success = true

                    })
                    .catch((error)=>{
                        this.warnings = error.response.data;
                    })
            }
        }





    }
</script>

<style scoped>
</style>