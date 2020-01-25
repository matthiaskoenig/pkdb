<template>
    <div v-if="verification_message.length > 0">
        {{verification_message}}
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
                let warnings = [];
                if ("key" in this.warnings){
                    warnings = this.warnings["key"]
                }
                return warnings;
            },
            verification_key() {
                return this.$route.params.id;
            },
        },
        methods: {
            verify: function(){
                this.warnings = {};
                this.success = false;

                const payload = {
                    "key": this.verification_key
                };
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