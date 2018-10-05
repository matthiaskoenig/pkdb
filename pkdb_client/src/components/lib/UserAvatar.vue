<template>
    <span id="user-avatar">
        <v-avatar color="red" size="35" :title="username">
            <img v-if="src" :src="src"/>
            <span v-if="!src" class="white--text headline" >{{ initials }}</span>
        </v-avatar>
    </span>
</template>

<script>
    export default {
        name: "UserAvatar",
        props: {
            user: {
                type: Object,
                required: true
            }
        },
        computed: {
            username() {
                return this.user.first_name + ' ' + this.user.last_name;
            },
            initials() {
                return this.user.first_name[0] + this.user.last_name[0];
            },
            src() {
                var img_dir = '/assets/images/avatars/';
                if (this.initials == 'MK'){
                    return img_dir + 'koenig_128.png';
                } else if (this.initials == 'JG'){
                    return img_dir + 'grzegorzewski_128.png';
                }
                return null;
            }

        }
    }
</script>

<style scoped>

</style>