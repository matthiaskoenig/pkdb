<template>
    <div>
        <div v-if="verification_message.length > 0">
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
                verification_message:[],
                success:false

            }
        },

        computed: {
            key_warnings(){
                if ("key" in this.warnings){
                    return this.warnings["key"]
                }
                else {
                    return []
                }
            },

            verification_key() {
                return this.$route.params.id;

            },



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
                        this.verification_message = this.verification_m();
                    });
            },
            verification_m(){
                if (this.email){
                    return ["Your email " + this.email + " has been verified. You can now login."]
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